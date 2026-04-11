import asyncio
import os
import json
import httpx
from openai import OpenAI

# ── Environment config ────────────────────────────────────────────────────────
API_KEY       = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL  = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME    = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
ENV_URL       = os.getenv("OPENENV_BASE_URL") or os.getenv("ENV_URL", "http://127.0.0.1:7860")
ENV_URL       = ENV_URL.rstrip("/")

# ── Logging helpers (required format) ────────────────────────────────────────
def log_start(task):
    print(f"[START] task={task}", flush=True)

def log_step(step, reward):
    print(f"[STEP] step={step} reward={reward:.4f}", flush=True)

def log_end(task, score, steps):
    print(f"[END] task={task} score={score:.4f} steps={steps}", flush=True)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an elite Site Reliability Engineer (SRE) AI Agent.
Your job: diagnose and resolve a critical production incident before system health hits 0%.
Each wrong action drops health by 15%. You have max 8 steps.

AVAILABLE COMMANDS (use exact spelling):
- get_logs      → target: exact service name (e.g. "auth-service-1234", "database", "ingress-nginx", "frontend-service", "payment-gateway", "redis-cache-cluster")
- get_metrics   → target: exact service name
- run_top       → target: exact node name (e.g. "worker-node-5")
- restart_pod   → target: exact pod name from the alert
- rollback_deploy → target: "database" (never add version numbers)
- block_ip      → target: exact IP address found in logs
- kill_process  → target: exact PID number found in run_top output
- flush_cache   → target: "redis-cache-cluster"

STRATEGY RULES:
1. Read the alert carefully — it tells you WHAT and WHERE.
2. If you are not 100% sure, use get_logs first to find the exact target.
3. Never repeat the same action twice.
4. For cascading failures: trace frontend → payment-gateway → redis-cache-cluster.
5. For OOM: run_top on the node, find the java PID, kill_process it.
6. For DDoS: get_logs on ingress-nginx, find the attacker IP, block_ip it.

RESPONSE FORMAT — valid JSON only, no markdown:
{"thought": "your reasoning here", "command": "exact_command", "target": "exact_target"}"""

# ── Agent loop ────────────────────────────────────────────────────────────────
async def run_task(client, http, task_name):
    log_start(task_name)
    rewards = []
    history = []
    success = False
    step = 0

    try:
        res = await http.post(f"{ENV_URL}/reset?task={task_name}", timeout=15.0)
        data = res.json()
        obs = data["observation"]
    except Exception as e:
        print(f"[ERROR] Could not reset task {task_name}: {e}", flush=True)
        log_end(task_name, 0.0, 0)
        return 0.0

    for step in range(1, 9):
        history_text = "\n".join(history[-4:]) if history else "None"
        terminal = obs.get("terminal_output", "")[-2000:]

        user_prompt = (
            f"ALERT: {obs.get('active_alerts', 'None')}\n"
            f"HEALTH: {obs.get('system_health', 100)}%\n"
            f"TERMINAL:\n{terminal}\n"
            f"HISTORY:\n{history_text}\n"
            f"Your JSON action:"
        )

        # LLM call with retry
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
                # Extract JSON even if wrapped in markdown
                if "{" in raw and "}" in raw:
                    raw = raw[raw.find("{"):raw.rfind("}") + 1]
                parsed = json.loads(raw)
                thought = parsed.get("thought", "")
                print(f"[THOUGHT] step={step} task={task_name}: {thought[:120]}", flush=True)
                server_action = {
                    "command": parsed.get("command", "get_logs"),
                    "target":  parsed.get("target",  "frontend-service")
                }
                break
            except Exception:
                if attempt == 2:
                    print(f"[WARN] LLM parse failed step={step}, using fallback", flush=True)
                else:
                    await asyncio.sleep(2)

        # Step the environment
        try:
            step_res = await http.post(f"{ENV_URL}/step", json=server_action, timeout=15.0)
            step_data = step_res.json()
            obs    = step_data["observation"]
            reward = float(step_data["reward"])
            done   = step_data["done"]
        except Exception as e:
            print(f"[ERROR] step failed: {e}", flush=True)
            reward = 0.05
            done   = True

        rewards.append(reward)
        log_step(step, reward)

        last_line = obs.get("terminal_output", "").split("\n")[-1]
        history.append(f"Step {step}: {server_action['command']}({server_action['target']}) → {last_line[:80]}")

        if done:
            if obs.get("system_health", 0) > 0 and reward >= 0.90:
                success = True
            break

    # Score calculation
    max_reward = (0.2 * (step - 1)) + 0.95
    total      = sum(rewards)
    score      = max(0.05, min(0.95, total / max_reward)) if max_reward > 0 else 0.05
    if not success:
        score = max(0.05, score * 0.6)

    log_end(task_name, score, step)
    return score


async def main():
    if not API_KEY:
        print("[ERROR] HF_TOKEN not set. Add it in HuggingFace Space secrets.", flush=True)
        return

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    tasks  = ["easy", "medium", "hard", "extreme", "insane"]
    scores = []

    async with httpx.AsyncClient() as http:
        for task in tasks:
            score = await run_task(client, http, task)
            scores.append(score)
            await asyncio.sleep(1)

    print("\n" + "=" * 55, flush=True)
    print("KUBESRE AGENT FINAL RESULTS", flush=True)
    print("=" * 55, flush=True)
    for task, score in zip(tasks, scores):
        status = "RESOLVED" if score >= 0.5 else "FAILED"
        print(f"{task.upper():<10} | {status:<10} | score={score:.4f}", flush=True)
    avg = sum(scores) / len(scores)
    print("=" * 55, flush=True)
    print(f"AVERAGE SCORE: {avg:.4f}", flush=True)
    print("=" * 55, flush=True)

if __name__ == "__main__":
    asyncio.run(main())
