import asyncio
import os
import json
from typing import List, Optional
from openai import OpenAI
import httpx

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_URL = os.getenv("ENV_URL", "http://127.0.0.1:7860")

# EXACT log format required by hackathon
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

async def main():
    if not API_KEY:
        print("ERROR: HF_TOKEN missing.", flush=True)
        return

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    task_name = "insane"
    log_start(task=task_name, env="sre-incident-env", model=MODEL_NAME)

    rewards = []
    history = []
    success = False

    system_prompt = """You are an elite Site Reliability Engineer (SRE) AI Agent.
Your objective is to diagnose and resolve a critical server incident before health reaches 0%.

# AVAILABLE TOOLS & STRICT SYNTAX:
1. "get_metrics" - Target: exact service name
2. "get_logs" - Target: exact service name
3. "run_top" - Target: exact node name (e.g., "worker-node-5")
4. "restart_pod" - Target: exact pod name (e.g., "auth-service-1234")
5. "rollback_deploy" - Target: exact service name ONLY (e.g., "database")
6. "block_ip" - Target: exact IP address
7. "kill_process" - Target: exact numerical PID
8. "flush_cache" - Target: "redis-cache-cluster"

# INCIDENT PLAYBOOK:
- HighLatency Alert: Extract pod name from alert → use "restart_pod"
- DatabaseConnectionFailing: use "rollback_deploy" on "database"
- TrafficSpike/DDoS: get_logs on ingress-nginx → find IP → block_ip
- OutOfMemory: run_top on node from alert → find java PID → kill_process
- Checkout 500 errors: get_logs frontend-service → payment-gateway → redis-cache-cluster → flush_cache

# COGNITIVE DIRECTIVES:
- BREADCRUMBS: Follow log clues to downstream services
- NOISE FILTERING: Ignore HTTP 200/304. Look ONLY for [FATAL], [ERROR], OOM
- SELF-CORRECTION: If previous action returned [ERROR], fix target immediately

Respond ONLY with valid JSON. No markdown.
{"thought": "reasoning here", "command": "command_here", "target": "target_here"}"""

    async with httpx.AsyncClient() as http:
        try:
            res = await http.post(f"{ENV_URL}/reset?task={task_name}", timeout=10.0)
            obs = res.json()["observation"]
        except Exception:
            print(f"Failed to connect to {ENV_URL}.", flush=True)
            return

        for step in range(1, 9):
            history_text = "\n".join(history[-4:]) if history else "None"
            terminal_out = obs.get('terminal_output', '')
            terminal_snippet = terminal_out[-1500:] if terminal_out else "None"

            user_prompt = (
                f"Alert: {obs.get('active_alerts', 'None')}\n"
                f"Health: {obs.get('system_health', 'Unknown')}%\n"
                f"Terminal: {terminal_snippet}\n"
                f"Recent History:\n{history_text}\n"
                f"Action JSON:"
            )

            error = None
            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0,
                    max_tokens=200
                )
                action_text = completion.choices[0].message.content.strip()
                if "{" in action_text and "}" in action_text:
                    action_text = action_text[action_text.find("{"):action_text.rfind("}") + 1]
                action_json = json.loads(action_text)
                thought = action_json.get("thought", "No thought.")
                print(f"\n🧠 [AI THOUGHT]: {thought}", flush=True)
                server_action = {
                    "command": action_json.get("command", "error"),
                    "target": action_json.get("target", "error")
                }
            except Exception:
                server_action = {"command": "error", "target": "error"}
                error = "JSON Parse Error"

            try:
                step_res = await http.post(f"{ENV_URL}/step", json=server_action, timeout=10.0)
                step_data = step_res.json()
                obs = step_data["observation"]
                reward = step_data["reward"]
                done = step_data["done"]
            except Exception:
                reward = 0.05
                done = True
                error = "Env connection failed"

            rewards.append(reward)
            log_action = f"{server_action['command']}('{server_action['target']}')"
            log_step(step, log_action, reward, done, error)
            history.append(f"Step {step}: ran {log_action} -> {obs.get('terminal_output','')[-100:]}")

            if done:
                if obs.get("system_health", 0) > 0 and reward >= 0.90:
                    success = True
                break

        max_possible_reward = (0.2 * (step - 1)) + 0.95
        total_reward = sum(rewards)
        score = total_reward / max_possible_reward if max_possible_reward > 0 else 0.05
        score = max(0.05, min(0.95, score))
        if not success:
            score = max(0.05, score * 0.5)

        log_end(success, step, score, rewards)

if __name__ == "__main__":
    asyncio.run(main())
