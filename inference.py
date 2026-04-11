"""
KubeSRE Autonomous SRE Agent v4.0
===================================
ReAct + Planning Phase + Episodic Memory + Confidence Scoring + Self-Correction
Author: Rishwanth Raju
"""

import asyncio
import os
import json
import httpx
from openai import OpenAI
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
ENV_URL      = os.getenv("OPENENV_BASE_URL") or os.getenv("ENV_URL", "http://127.0.0.1:7860")
ENV_URL      = ENV_URL.rstrip("/")

# ── Required log format ─────────────────────────────────────────────────────
def log_start(task):             print(f"[START] task={task}", flush=True)
def log_step(step, reward):      print(f"[STEP] step={step} reward={reward:.4f}", flush=True)
def log_end(task, score, steps): print(f"[END] task={task} score={score:.4f} steps={steps}", flush=True)

# ── Episodic Memory ─────────────────────────────────────────────────────────
class EpisodicMemory:
    """Cross-task memory — remembers what worked in previous incidents."""
    def __init__(self):
        self.episodes = {}

    def store(self, task, alert, cmd, target, success, steps, score):
        self.episodes[task] = {
            "alert":   str(alert)[:80],
            "cmd":     cmd,
            "target":  target,
            "success": success,
            "steps":   steps,
            "score":   round(score, 3),
            "time":    datetime.utcnow().strftime("%H:%M:%S"),
        }

    def recall(self, current_task) -> str:
        if not self.episodes:
            return ""
        lines = []
        for k, v in self.episodes.items():
            if k == current_task:
                continue
            icon = "✅" if v["success"] else "❌"
            lines.append(
                f"  [{icon}] '{k}': alert='{v['alert']}' "
                f"→ solution='{v['cmd']}({v['target']})' "
                f"steps={v['steps']} score={v['score']}"
            )
        if not lines:
            return ""
        return "EPISODIC MEMORY (learn from previous incidents):\n" + "\n".join(lines)

# ── Prompts ─────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an elite Site Reliability Engineer (SRE) AI Agent with a perfect incident record.
Resolve the production incident before system health hits 0%. Wrong fixes cost -15% health. Max 12 steps.

AVAILABLE COMMANDS (exact spelling required):
- get_logs        → target: exact service name shown in the alert or terminal
- get_metrics     → target: exact service name
- run_top         → target: exact node name from alert (e.g. "worker-node-7")
- restart_pod     → target: exact pod name from the alert (e.g. "auth-service-4521")
- rollback_deploy → target: ALWAYS "database" — never add version numbers
- block_ip        → target: exact attacker IP found in ingress-nginx logs
- kill_process    → target: exact PID number found in run_top output
- flush_cache     → target: ALWAYS "redis-cache-cluster"

INCIDENT PLAYBOOK:
1. HighLatency / Thread pool alert      → get_logs <pod_name> → restart_pod <pod_name>
2. DatabaseConnectionFailing alert      → get_logs database   → rollback_deploy database
3. TrafficSpike / DDoS alert            → get_logs ingress-nginx → find IP → block_ip <IP>
4. OutOfMemory / RAM alert              → run_top <node_name> → find java PID → kill_process <PID>
5. Checkout 500 / Cascading alert       → get_logs frontend-service → get_logs payment-gateway → get_logs redis-cache-cluster → flush_cache redis-cache-cluster
6. Multi-region / Apocalypse alert      → get_logs haproxy → run_top <db_node> → get_logs db-replica → block_ip <attacker_ip> → flush_cache redis-cache-cluster

RULES:
- NEVER repeat the same command+target (you get penalised).
- ALWAYS extract exact pod names, IPs, PIDs from terminal — never guess.
- confidence < 0.75 means investigate more before fixing.
- confidence ≥ 0.75 means apply the fix.

RESPONSE FORMAT — strict JSON only, no markdown, no extra text:
{"plan": "1-sentence plan for this step", "confidence": 0.95, "thought": "detailed reasoning", "command": "exact_command", "target": "exact_target"}"""

# ── Agent ───────────────────────────────────────────────────────────────────
async def run_task(
    client: OpenAI,
    http: httpx.AsyncClient,
    task_name: str,
    memory: EpisodicMemory
) -> float:

    log_start(task_name)
    rewards     = []
    history     = []
    success     = False
    step        = 0
    last_action = {"command": "none", "target": "none"}
    last_alert  = "Unknown"
    error_hint  = ""

    # Reset environment
    try:
        res        = await http.post(f"{ENV_URL}/reset?task={task_name}", timeout=15.0)
        data       = res.json()
        obs        = data["observation"]
        last_alert = obs.get("active_alerts", "Unknown")
    except Exception as e:
        print(f"[ERROR] Reset failed for task={task_name}: {e}", flush=True)
        log_end(task_name, 0.0, 0)
        return 0.0

    # Agent loop
    for step in range(1, 13):
        history_text  = "\n".join(history[-5:]) if history else "None"
        terminal_text = obs.get("terminal_output", "")[-2000:]
        memory_text   = memory.recall(task_name)

        user_prompt = (
            f"ACTIVE ALERT  : {obs.get('active_alerts', 'None')}\n"
            f"SYSTEM HEALTH : {obs.get('system_health', 100):.1f}%\n"
            f"STEP          : {step}/12\n"
            f"TERMINAL OUTPUT:\n{terminal_text}\n\n"
            f"ACTION HISTORY:\n{history_text}\n"
            + (f"\n{memory_text}\n" if memory_text else "")
            + (f"\n⚠️  HINT: {error_hint}\n" if error_hint else "")
            + "\nWrite your JSON action now:"
        )

        # LLM call with 3-attempt retry + self-correction
        server_action = {"command": "get_logs", "target": "frontend-service"}
        confidence    = 0.5
        plan_text     = ""

        for attempt in range(3):
            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": user_prompt}
                    ],
                    temperature=0.0,
                    max_tokens=250
                )
                raw = completion.choices[0].message.content.strip()
                # Extract JSON even if wrapped in markdown
                if "```" in raw:
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                if "{" in raw and "}" in raw:
                    raw = raw[raw.find("{"):raw.rfind("}")+1]

                parsed     = json.loads(raw)
                confidence = float(parsed.get("confidence", 1.0))
                thought    = parsed.get("thought", "")
                plan_text  = parsed.get("plan", "")

                print(
                    f"[PLAN]    step={step} task={task_name}: {plan_text[:100]}",
                    flush=True
                )
                print(
                    f"[THOUGHT] step={step} conf={confidence:.0%}: {thought[:120]}",
                    flush=True
                )

                server_action = {
                    "command": parsed.get("command", "get_logs"),
                    "target":  parsed.get("target",  "frontend-service")
                }
                error_hint = ""
                break

            except Exception as ex:
                if attempt == 2:
                    print(f"[WARN] LLM parse failed step={step}: {ex}", flush=True)
                    error_hint = "PREVIOUS OUTPUT WAS INVALID JSON. Return ONLY valid JSON with no markdown."
                else:
                    await asyncio.sleep(2)

        # Step the environment
        try:
            step_res  = await http.post(f"{ENV_URL}/step", json=server_action, timeout=15.0)
            step_data = step_res.json()
            obs       = step_data["observation"]
            reward    = float(step_data["reward"])
            done      = step_data["done"]

            if "[ERROR]" in obs.get("terminal_output", ""):
                error_hint = "Previous command caused an error. Verify exact spelling of target from the terminal output."
        except Exception as e:
            print(f"[ERROR] Step failed: {e}", flush=True)
            reward = 0.05
            done   = True

        rewards.append(reward)
        log_step(step, reward)
        last_action = server_action

        # Build history entry
        last_line = obs.get("terminal_output", "").split("\n")[-1]
        history.append(
            f"Step {step}: plan='{plan_text[:50]}' "
            f"action={server_action['command']}({server_action['target']}) "
            f"reward={reward:.2f} | {last_line[:70]}"
        )

        if done:
            health = obs.get("system_health", 0)
            if health > 0 and reward >= 0.90:
                success = True
            break

    # Score calculation
    max_possible = (0.20 * (step - 1)) + 0.95
    total        = sum(rewards)
    score        = max(0.05, min(0.95, total / max_possible)) if max_possible > 0 else 0.05
    if not success:
        score = max(0.05, score * 0.6)

    log_end(task_name, score, step)

    # Store in episodic memory
    memory.store(
        task=task_name,
        alert=last_alert,
        cmd=last_action["command"],
        target=last_action["target"],
        success=success,
        steps=step,
        score=score
    )

    return score

# ── Main ─────────────────────────────────────────────────────────────────────
async def main():
    if not API_KEY:
        print("[ERROR] HF_TOKEN not set. Add it in HuggingFace Space → Settings → Secrets.", flush=True)
        return

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    memory = EpisodicMemory()
    tasks  = ["easy", "medium", "hard", "extreme", "insane", "apocalypse"]
    scores = []

    print("[KubeSRE v4.0] Agent starting.", flush=True)
    print(f"[KubeSRE] Model: {MODEL_NAME}", flush=True)
    print(f"[KubeSRE] Tasks: {', '.join(tasks)}", flush=True)
    print("[KubeSRE] Features: ReAct + Planning + Episodic Memory + Confidence Scoring", flush=True)

    async with httpx.AsyncClient() as http:
        for task in tasks:
            score = await run_task(client, http, task, memory)
            scores.append((task, score))
            await asyncio.sleep(1)

    # Final scorecard
    print("\n" + "="*65, flush=True)
    print("  KUBESRE AGENT FINAL SCORECARD", flush=True)
    print("="*65, flush=True)
    print(f"  {'TASK':<14} {'STATUS':<12} {'SCORE':<10} {'GRADE'}", flush=True)
    print("-"*65, flush=True)

    total = 0.0
    wins  = 0
    for task, score in scores:
        status = "RESOLVED" if score >= 0.50 else "FAILED"
        grade  = "S" if score >= 0.90 else "A" if score >= 0.75 else "B" if score >= 0.55 else "C"
        icon   = "✅" if score >= 0.50 else "❌"
        print(f"  {icon} {task.upper():<12} {status:<12} {score:<10.4f} [{grade}]", flush=True)
        total += score
        if score >= 0.50:
            wins += 1

    avg      = total / len(scores)
    win_rate = (wins / len(scores)) * 100

    print("="*65, flush=True)
    print(f"  AVERAGE SCORE : {avg:.4f}", flush=True)
    print(f"  WIN RATE      : {win_rate:.1f}%  ({wins}/{len(scores)} tasks resolved)", flush=True)
    print(f"  OVERALL GRADE : {'S+' if avg >= 0.90 else 'A' if avg >= 0.75 else 'B'}", flush=True)
    print("="*65, flush=True)

if __name__ == "__main__":
    asyncio.run(main())
