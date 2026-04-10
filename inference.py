import asyncio
import os
import json
import re
from typing import Dict, Any, List
from openai import OpenAI
import httpx
from datetime import datetime, UTC

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_URL = os.getenv("ENV_URL", "http://127.0.0.1:7860")

TASK_NAMES = ["easy", "medium", "hard", "extreme", "insane"]

VALID_COMMANDS = {
    "get_metrics",
    "get_logs",
    "run_top",
    "restart_pod",
    "rollback_deploy",
    "block_ip",
    "kill_process",
    "flush_cache",
}

KNOWN_SERVICES = {
    "auth-service",
    "database",
    "frontend-service",
    "payment-gateway",
    "redis-cache-cluster",
    "ingress-nginx",
}

IP_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
PID_RE = re.compile(r"^\d{2,10}$")
NODE_RE = re.compile(r"^worker-node-\d+$")
POD_RE = re.compile(r"^[a-z0-9-]+$")


def log_start(task: str) -> None:
    print(f"[START] task={task}", flush=True)


def log_step(step: int, reward: float, action: str) -> None:
    print(f"[STEP] step={step} reward={reward:.3f} action={action}", flush=True)


def log_end(task: str, score: float, steps: int, success: bool) -> None:
    print(f"[END] task={task} score={score:.3f} steps={steps} success={success}", flush=True)


class EpisodicMemory:
    def __init__(self) -> None:
        self.memory: Dict[str, dict] = {}

    def store(
        self,
        task: str,
        alert: str,
        solution_cmd: str,
        solution_target: str,
        success: bool,
        steps: int,
    ) -> None:
        self.memory[task] = {
            "alert": alert,
            "solution_cmd": solution_cmd,
            "solution_target": solution_target,
            "success": success,
            "steps": steps,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def recall(self, current_task: str) -> str:
        if not self.memory:
            return "No previous incident memory available."

        memories = []
        for task, data in self.memory.items():
            if task != current_task:
                status = "RESOLVED" if data["success"] else "FAILED"
                memories.append(
                    f"[{status}] Task '{task}': Alert was '{data['alert'][:80]}'. "
                    f"Final action was '{data['solution_cmd']}' on '{data['solution_target']}' in {data['steps']} steps."
                )

        if not memories:
            return "No previous incident memory available."

        return "EPISODIC MEMORY (What worked before):\n" + "\n".join(memories)


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def get_alert_text(obs: Dict[str, Any]) -> str:
    return safe_str(obs.get("active_alerts", ""))


def get_terminal_text(obs: Dict[str, Any]) -> str:
    return safe_str(obs.get("terminal_output", ""))


def extract_worker_node(text: str) -> str:
    match = re.search(r"(worker-node-\d+)", text or "")
    return match.group(1) if match else ""


def extract_ip(text: str) -> str:
    match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text or "")
    return match.group(0) if match else ""


def extract_pid(text: str) -> str:
    pid_matches = re.findall(r"\b\d{4,10}\b", text or "")
    return pid_matches[-1] if pid_matches else ""


def action_signature(action: Dict[str, str]) -> str:
    return f"{action.get('command', '')}::{action.get('target', '')}"


def was_action_already_used(action: Dict[str, str], history_actions: List[str]) -> bool:
    return action_signature(action) in history_actions


def infer_safe_fallback(obs: Dict[str, Any], history_actions: List[str]) -> Dict[str, str]:
    alert = get_alert_text(obs).lower()
    terminal = get_terminal_text(obs)

    if "database" in alert:
        candidate = {"command": "get_logs", "target": "database"}
        if not was_action_already_used(candidate, history_actions):
            return candidate

    if "frontend-service" in alert or "checkout" in alert or "500" in alert:
        chain = [
            {"command": "get_logs", "target": "frontend-service"},
            {"command": "get_logs", "target": "payment-gateway"},
            {"command": "get_logs", "target": "redis-cache-cluster"},
            {"command": "flush_cache", "target": "redis-cache-cluster"},
        ]
        for candidate in chain:
            if not was_action_already_used(candidate, history_actions):
                return candidate

    if "worker-node" in alert or "oom" in alert:
        node = extract_worker_node(get_alert_text(obs)) or extract_worker_node(terminal)
        if node:
            candidate = {"command": "run_top", "target": node}
            if not was_action_already_used(candidate, history_actions):
                return candidate

    if "ddos" in alert or "traffic" in alert or "ingress" in alert:
        candidate = {"command": "get_logs", "target": "ingress-nginx"}
        if not was_action_already_used(candidate, history_actions):
            return candidate

    if "auth-service" in alert or "latency" in alert:
        candidate = {"command": "get_metrics", "target": "auth-service"}
        if not was_action_already_used(candidate, history_actions):
            return candidate

    default_chain = [
        {"command": "get_logs", "target": "database"},
        {"command": "get_logs", "target": "frontend-service"},
        {"command": "get_logs", "target": "ingress-nginx"},
        {"command": "get_metrics", "target": "auth-service"},
    ]
    for candidate in default_chain:
        if not was_action_already_used(candidate, history_actions):
            return candidate

    return {"command": "get_logs", "target": "database"}


def validate_and_repair_action(
    action_json: Dict[str, Any],
    obs: Dict[str, Any],
    history_actions: List[str],
) -> (Dict[str, str], str):
    command = safe_str(action_json.get("command", ""))
    target = safe_str(action_json.get("target", ""))
    confidence_raw = action_json.get("confidence", 1.0)

    try:
        confidence = float(confidence_raw)
    except Exception:
        confidence = 1.0

    if command not in VALID_COMMANDS:
        fallback = infer_safe_fallback(obs, history_actions)
        return fallback, f"Invalid command '{command}'. Replaced with safe fallback."

    if confidence < 0.70 and command not in {"get_logs", "get_metrics", "run_top"}:
        fallback = infer_safe_fallback(obs, history_actions)
        return fallback, f"Low confidence ({confidence:.2f}). Replaced with reconnaissance action."

    if command == "rollback_deploy":
        if target != "database":
            repaired = {"command": "rollback_deploy", "target": "database"}
            return repaired, "Repaired rollback_deploy target to exact service 'database'."

    elif command == "flush_cache":
        if target != "redis-cache-cluster":
            repaired = {"command": "flush_cache", "target": "redis-cache-cluster"}
            return repaired, "Repaired flush_cache target to 'redis-cache-cluster'."

    elif command == "kill_process":
        if not PID_RE.fullmatch(target):
            pid = extract_pid(get_terminal_text(obs))
            if pid:
                repaired = {"command": "kill_process", "target": pid}
                return repaired, f"Repaired kill_process target to PID '{pid}'."
            fallback = infer_safe_fallback(obs, history_actions)
            return fallback, f"Invalid PID target '{target}'. Replaced with safe fallback."

    elif command == "block_ip":
        if not IP_RE.fullmatch(target):
            ip = extract_ip(get_terminal_text(obs))
            if ip:
                repaired = {"command": "block_ip", "target": ip}
                return repaired, f"Repaired block_ip target to IP '{ip}'."
            fallback = infer_safe_fallback(obs, history_actions)
            return fallback, f"Invalid IP target '{target}'. Replaced with safe fallback."

    elif command == "run_top":
        if not NODE_RE.fullmatch(target):
            node = extract_worker_node(get_alert_text(obs)) or extract_worker_node(get_terminal_text(obs))
            if node:
                repaired = {"command": "run_top", "target": node}
                return repaired, f"Repaired run_top target to '{node}'."
            fallback = infer_safe_fallback(obs, history_actions)
            return fallback, f"Invalid node target '{target}'. Replaced with safe fallback."

    elif command == "get_logs":
        if target not in KNOWN_SERVICES:
            fallback = infer_safe_fallback(obs, history_actions)
            return fallback, f"Invalid get_logs target '{target}'. Replaced with safe fallback."

    elif command == "get_metrics":
        if target not in KNOWN_SERVICES:
            fallback = infer_safe_fallback(obs, history_actions)
            return fallback, f"Invalid get_metrics target '{target}'. Replaced with safe fallback."

    elif command == "restart_pod":
        if not POD_RE.fullmatch(target):
            fallback = infer_safe_fallback(obs, history_actions)
            return fallback, f"Invalid pod target '{target}'. Replaced with safe fallback."

    repaired_action = {"command": command, "target": target}

    if was_action_already_used(repaired_action, history_actions):
        fallback = infer_safe_fallback(obs, history_actions)
        if action_signature(fallback) != action_signature(repaired_action):
            return fallback, f"Repeated action '{command}({target})'. Replaced with new fallback."

    return repaired_action, ""


def build_history_text(history_lines: List[str]) -> str:
    if not history_lines:
        return "None"
    return "\n".join(history_lines[-5:])


def build_system_prompt() -> str:
    return """You are an elite Site Reliability Engineer (SRE) AI Agent with a perfect incident resolution mindset.
Your objective is to diagnose and resolve a critical server incident before health reaches 0%.

# AVAILABLE TOOLS & STRICT SYNTAX:
1. "get_metrics" - Target: exact service name (e.g., "auth-service", "database", "ingress-nginx")
2. "get_logs" - Target: exact service name
3. "run_top" - Target: exact node name (e.g., "worker-node-5")
4. "restart_pod" - Target: exact pod name (e.g., "auth-service-1234")
5. "rollback_deploy" - Target: exact service name ONLY (e.g., "database"). NEVER append version numbers.
6. "block_ip" - Target: exact IP address
7. "kill_process" - Target: exact numerical PID
8. "flush_cache" - Target: "redis-cache-cluster"

# HARD RULES:
- Output ONLY valid JSON.
- Never output markdown.
- Never invent command names.
- Never append extra syntax to rollback_deploy.
- If confidence is low, gather more evidence first.
- Do not repeat the same action on the same target if it already failed.

# PLAYBOOKS:
- Database auth failure -> rollback_deploy on "database"
- DDoS / traffic spike -> get_logs on "ingress-nginx", extract attacker IP, then block_ip
- OOM on worker-node -> run_top on exact worker node, extract PID, then kill_process
- Checkout / frontend 500 -> frontend-service -> payment-gateway -> redis-cache-cluster -> flush_cache
- Latency / unstable pod -> inspect metrics/logs, then restart_pod only when exact pod is known

# JSON FORMAT:
{"confidence": 0.95, "thought": "short reasoning", "command": "get_logs", "target": "database"}"""


async def run_task(
    client: OpenAI,
    http: httpx.AsyncClient,
    task_name: str,
    memory: EpisodicMemory,
    all_results: List[Dict[str, Any]],
) -> None:
    log_start(task=task_name)

    rewards: List[float] = []
    history_lines: List[str] = []
    history_actions: List[str] = []
    success = False
    current_step = 0
    error_msg_for_prompt = ""
    last_alert = "Unknown"
    final_action = {"command": "none", "target": "none"}
    obs: Dict[str, Any] = {
        "active_alerts": "",
        "system_health": 100,
        "terminal_output": "",
    }

    try:
        res = await http.post(f"{ENV_URL}/reset?task={task_name}", timeout=15.0)
        res.raise_for_status()
        obs = res.json()["observation"]
        last_alert = obs.get("active_alerts", "Unknown")
    except Exception as e:
        print(f"[ERROR] Failed to reset task '{task_name}': {e}", flush=True)
        all_results.append({
            "task": task_name,
            "success": False,
            "score": 0.05,
            "steps": 0,
        })
        return

    system_prompt = build_system_prompt()

    for step in range(1, 9):
        current_step = step
        history_text = build_history_text(history_lines)
        terminal_out = get_terminal_text(obs)
        terminal_snippet = terminal_out[-1500:] if terminal_out else "None"
        memory_context = memory.recall(task_name)

        user_prompt = (
            f"Alert: {obs.get('active_alerts', 'None')}\n"
            f"Health: {obs.get('system_health', 'Unknown')}%\n"
            f"Terminal: {terminal_snippet}\n"
            f"Recent History:\n{history_text}\n"
            f"{memory_context}\n"
            f"{error_msg_for_prompt}\n"
            f"Action JSON:"
        )

        max_retries = 3
        server_action = infer_safe_fallback(obs, history_actions)
        thought = "Fallback reasoning."
        confidence = 0.50

        for attempt in range(max_retries):
            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.0,
                    max_tokens=250,
                )

                action_text = completion.choices[0].message.content.strip()

                if "{" in action_text and "}" in action_text:
                    action_text = action_text[action_text.find("{"):action_text.rfind("}") + 1]

                action_json = json.loads(action_text)
                thought = safe_str(action_json.get("thought", "No thought provided."))

                try:
                    confidence = float(action_json.get("confidence", 1.0))
                except Exception:
                    confidence = 1.0

                repaired_action, validation_note = validate_and_repair_action(
                    action_json, obs, history_actions
                )
                server_action = repaired_action

                print(
                    f"\n🧠 [AI THOUGHT - {task_name.upper()}] "
                    f"(Confidence: {confidence:.0%}): {thought}",
                    flush=True,
                )

                if validation_note:
                    print(f"[GUARDRAIL] {validation_note}", flush=True)
                    error_msg_for_prompt = f"PREVIOUS FAILED: {validation_note}"
                else:
                    error_msg_for_prompt = ""

                break

            except Exception as e:
                if attempt == max_retries - 1:
                    server_action = infer_safe_fallback(obs, history_actions)
                    error_msg_for_prompt = (
                        "PREVIOUS FAILED: Invalid JSON or response parsing issue. "
                        "Using safe fallback action."
                    )
                    print(f"[RETRY-FALLBACK] {e}", flush=True)
                else:
                    await asyncio.sleep(1.5)

        final_action = server_action

        try:
            step_res = await http.post(f"{ENV_URL}/step", json=server_action, timeout=15.0)
            step_res.raise_for_status()
            step_data = step_res.json()
            obs = step_data["observation"]
            reward = float(step_data["reward"])
            done = bool(step_data["done"])

            terminal_after = get_terminal_text(obs)
            if "[ERROR]" in terminal_after:
                error_msg_for_prompt = (
                    "PREVIOUS FAILED: Command caused an error. "
                    "Use exact target spelling and valid syntax."
                )

        except Exception as e:
            print(f"[ERROR] Step execution failed: {e}", flush=True)
            reward = 0.05
            done = True
            obs = {
                "active_alerts": last_alert,
                "system_health": 0,
                "terminal_output": f"[ERROR] Step execution failed: {e}",
            }

        rewards.append(reward)
        action_text = f"{server_action['command']}('{server_action['target']}')"
        history_actions.append(action_signature(server_action))

        hist_term = get_terminal_text(obs)
        hist_line = hist_term.split("\n")[-1] if hist_term else "None"
        history_lines.append(
            f"Step {step}: ran {action_text} -> Result: {hist_line[:140]}"
        )

        log_step(step, reward, action_text)

        if done:
            if "system_health" in obs and float(obs["system_health"]) > 0 and reward >= 0.90:
                success = True
            break

    max_possible_reward = (0.2 * max(current_step - 1, 0)) + 0.95
    total_reward = sum(rewards)
    score = total_reward / max_possible_reward if max_possible_reward > 0 else 0.05
    score = max(0.05, min(0.95, score))
    if not success:
        score = max(0.05, score * 0.5)

    log_end(task=task_name, score=score, steps=current_step, success=success)

    memory.store(
        task=task_name,
        alert=last_alert,
        solution_cmd=final_action["command"],
        solution_target=final_action["target"],
        success=success,
        steps=current_step,
    )

    all_results.append({
        "task": task_name,
        "success": success,
        "score": score,
        "steps": current_step,
    })

    try:
        await http.get(f"{ENV_URL}/grade/{task_name}", timeout=10.0)
    except Exception:
        pass


async def main() -> None:
    if not API_KEY:
        print("ERROR: HF_TOKEN missing. Please set it in terminal.", flush=True)
        return

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    memory = EpisodicMemory()
    all_results: List[Dict[str, Any]] = []

    print("\n" + "=" * 60, flush=True)
    print("🚨 KUBESRE AUTONOMOUS AGENT INITIALIZED 🚨", flush=True)
    print("=" * 60, flush=True)

    async with httpx.AsyncClient() as http:
        for task_name in TASK_NAMES:
            await run_task(
                client=client,
                http=http,
                task_name=task_name,
                memory=memory,
                all_results=all_results,
            )
            await asyncio.sleep(1)

    print("\n" + "=" * 60, flush=True)
    print("📊 KUBESRE AGENT PERFORMANCE ANALYTICS", flush=True)
    print("=" * 60, flush=True)

    total_score = 0.0
    wins = 0

    for r in all_results:
        status = "✅ RESOLVED" if r["success"] else "❌ FAILED"
        print(
            f"{r['task'].upper():<10} | {status} | Score: {r['score']:.3f} | Steps: {r['steps']}",
            flush=True,
        )
        total_score += r["score"]
        if r["success"]:
            wins += 1

    avg = total_score / len(all_results) if all_results else 0.0
    win_rate = (wins / len(all_results)) * 100 if all_results else 0.0

    print("=" * 60, flush=True)
    print(f"🏆 WIN RATE: {win_rate:.1f}% | AVG SCORE: {avg:.3f}", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    asyncio.run(main())