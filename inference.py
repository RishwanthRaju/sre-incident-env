"""
KubeSRE Autonomous SRE Agent
=============================
ReAct + Episodic Memory + Confidence Scoring + Self-Correction
Author: Rishwanth Raju
"""

import asyncio
import os
import json
import httpx
from openai import OpenAI
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
ENV_URL      = os.getenv("OPENENV_BASE_URL") or os.getenv("ENV_URL", "http://127.0.0.1:7860")
ENV_URL      = ENV_URL.rstrip("/")

# ── Required log format ───────────────────────────────────────────────────────
def log_start(task):        print(f"[START] task={task}", flush=True)
def log_step(step, reward): print(f"[STEP] step={step} reward={reward:.4f}", flush=True)
def log_end(task, score, steps): print(f"[END] task={task} score={score:.4f} steps={steps}", flush=True)

# ── Episodic Memory ───────────────────────────────────────────────────────────
class EpisodicMemory:
    """Remembers what worked in previous tasks — like a real SRE engineer."""
    def __init__(self):
        self.episodes = {}

    def store(self, task, alert, cmd, target, success, steps):
        self.episodes[task] = {
            "alert": alert[:80], "cmd": cmd, "target": target,
            "success": success, "steps": steps,
            "time": datetime.utcnow().strftime("%H:%M:%S")
        }

    def recall(self, current_task) -> str:
        relevant = [
            f"  [{('✅' if v['success'] else '❌')}] Task '{k}': "
            f"Alert='{v['alert']}' → Solution='{v['cmd']}({v['target']})' in {v['steps']} steps"
            for k, v in self.episodes.items() if k != current_task
        ]
        if not relevant:
            return ""
        return "EPISODIC MEMORY (previous incidents):\n" + "\n".join(relevant)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an elite Site Reliability Engineer (SRE) AI Agent with a perfect incident resolution record.
Resolve the production incident before system health reaches 0%. Each wrong fix drops health by 15%. Max 8 steps.

AVAILABLE COMMANDS (exact spelling required):
- get_logs       → target: exact service name (e.g. "auth-service-4521", "ingress-nginx", "frontend-service")
- get_metrics    → target: exact service name
- run_top        → target: exact node name (e.g. "worker-node-7")
- restart_pod    → target: exact pod name from alert (e.g. "auth-service-4521")
- rollback_deploy→ target: "database" (NEVER append version numbers)
- block_ip       → target: exact IP from logs (e.g. "45.33.12.71")
- kill_process   → target: exact PID number from run_top (e.g. "98432")
- flush_cache    → target: "redis-cache-cluster"

STRATEGY PLAYBOOK:
- HighLatency alert       → get_logs on the pod name → restart_pod on exact pod name
- DatabaseConnection alert → get_logs on "database" → rollback_deploy on "database"
- TrafficSpike alert      → get_logs on "ingress-nginx" → find IP → block_ip on that IP
- OutOfMemory alert       → run_top on node from alert → find java PID → kill_process on PID
- Checkout 500 alert      → get_logs frontend-service → get_logs payment-gateway → get_logs redis-cache-cluster → flush_cache redis-cache-cluster

CONFIDENCE RULE:
- confidence < 0.75 → gather more info first (get_logs or run_top)
- confidence ≥ 0.75 → apply the fix directly

CRITICAL RULES:
1. NEVER repeat the same action (you get penalised).
2. Extract exact pod names, IPs, PIDs from terminal output — do NOT guess.
3. For rollback_deploy, target is ALWAYS just "database" — no version numbers.
4. For flush_cache, target is ALWAYS "redis-cache-cluster".

Respond ONLY with valid JSON, no markdown:
{"confidence": 0.95, "thought": "reasoning here", "command": "exact_command", "target": "exact_target"}"""

# ── Agent ─────────────────────────────────────────────────────────────────────
async def run_task(client, http, task_name, memory: EpisodicMemory) -> float:
    log_start(task_name)
    rewards = []
    history = []
    success = False
    step    = 0
    last_alert = "Unknown"
    last_action = {"command": "none", "target": "none"}
    error_hint  = ""

    try:
        res  = await http.post(f"{ENV_URL}/reset?task={task_name}", timeout=15.0)
        data = res.json()
        obs  = data["observation"]
        last_alert = obs.get("active_alerts", "Unknown")
    except Exception as e:
        print(f"[ERROR] Reset failed for {task_name}: {e}", flush=True)
        log_end(task_name, 0.0, 0)
        return 0.0

    for step in range(1, 9):
        history_text  = "\n".join(history[-4:]) if history else "None"
        terminal_text = obs.get("terminal_output", "")[-2000:]
        memory_text   = memory.recall(task_name)

        user_prompt = (
            f"ACTIVE ALERT: {obs.get('active_alerts', 'None')}\n"
            f"SYSTEM HEALTH: {obs.get('system_health', 100):.1f}%\n"
            f"TERMINAL OUTPUT:\n{terminal_text}\n\n"
            f"STEP HISTORY:\n{history_text}\n"
            + (f"\n{memory_text}\n" if memory_text else "")
            + (f"\nHINT: {error_hint}\n" if error_hint else "")
            + "\nYour JSON action:"
        )

        # LLM call with 3-attempt retry + self-correction
        server_action = {"command": "get_logs", "target": "frontend-service"}
        for attempt in range(3):
            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": user_prompt}
                    ],
                    temperature=0.0,
                    max_tokens=200
                )
                raw = completion.choices[0].message.content.strip()
                if "{" in raw and "}" in raw:
                    raw = raw[raw.find("{"):raw.rfind("}")+1]
                parsed     = json.loads(raw)
                confidence = parsed.get("confidence", 1.0)
                thought    = parsed.get("thought", "No thought.")
                print(f"[THOUGHT] step={step} task={task_name} conf={confidence:.0%}: {thought[:120]}", flush=True)
                server_action = {
                    "command": parsed.get("command", "get_logs"),
                    "target":  parsed.get("target",  "frontend-service")
                }
                error_hint = ""
                break
            except Exception as ex:
                if attempt == 2:
                    print(f"[WARN] LLM failed step={step}: {ex}", flush=True)
                    error_hint = "PREVIOUS JSON INVALID. Output ONLY valid JSON with no markdown."
                else:
                    await asyncio.sleep(2)

        # Step environment
        try:
            step_res  = await http.post(f"{ENV_URL}/step", json=server_action, timeout=15.0)
            step_data = step_res.json()
            obs       = step_data["observation"]
            reward    = float(step_data["reward"])
            done      = step_data["done"]
            if "[ERROR]" in obs.get("terminal_output", ""):
                error_hint = "Previous command caused an error. Check exact spelling of target."
        except Exception as e:
            print(f"[ERROR] Step failed: {e}", flush=True)
            reward = 0.05
            done   = True

        rewards.append(reward)
        log_step(step, reward)
        last_action = server_action

        last_line = obs.get("terminal_output", "").split("\n")[-1]
        history.append(f"Step {step}: {server_action['command']}({server_action['target']}) → reward={reward:.2f} | {last_line[:80]}")

        if done:
            health = obs.get("system_health", 0)
            if health > 0 and reward >= 0.90:
                success = True
            break

    # Score
    max_possible = (0.20 * (step - 1)) + 0.95
    total        = sum(rewards)
    score        = max(0.05, min(0.95, total / max_possible)) if max_possible > 0 else 0.05
    if not success:
        score = max(0.05, score * 0.6)

    log_end(task_name, score, step)

    memory.store(
        task=task_name, alert=last_alert,
        cmd=last_action["command"], target=last_action["target"],
        success=success, steps=step
    )

    return score

# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    if not API_KEY:
        print("[ERROR] HF_TOKEN not set. Add it in HuggingFace Space Secrets.", flush=True)
        return

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    memory = EpisodicMemory()
    tasks  = ["easy", "medium", "hard", "extreme", "insane"]
    scores = []

    print("[KubeSRE] Agent starting. Tasks: " + ", ".join(tasks), flush=True)

    async with httpx.AsyncClient() as http:
        for task in tasks:
            score = await run_task(client, http, task, memory)
            scores.append((task, score))
            await asyncio.sleep(1)

    print("\n" + "="*60, flush=True)
    print("KUBESRE AGENT FINAL RESULTS", flush=True)
    print("="*60, flush=True)
    total = 0.0
    for task, score in scores:
        status = "RESOLVED" if score >= 0.50 else "FAILED"
        print(f"{task.upper():<10} | {status:<10} | score={score:.4f}", flush=True)
        total += score
    avg = total / len(scores)
    print("="*60, flush=True)
    print(f"AVERAGE SCORE: {avg:.4f}", flush=True)
    print("="*60, flush=True)

if __name__ == "__main__":
    asyncio.run(main())
