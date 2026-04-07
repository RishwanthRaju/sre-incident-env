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
        print("ERROR: HF_TOKEN missing. Please set it in terminal.", flush=True)
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
1. "get_metrics" - Target: exact service name (e.g., "auth-service", "database", "ingress-nginx")
2. "get_logs" - Target: exact service name
3. "run_top" - Target: exact node name (e.g., "worker-node-5")
4. "restart_pod" - Target: exact pod name
5. "rollback_deploy" - Target: exact service name ONLY (e.g., "database") - Do NOT append version numbers!
6. "block_ip" - Target: exact IP address
7. "kill_process" - Target: exact numerical PID
8. "flush_cache" - Target: "redis-cache-cluster"

# COGNITIVE DIRECTIVES:
- BREADCRUMBS: If logs indicate a downstream failure (e.g., "Cannot communicate with redis"), you MUST investigate the downstream service next.
- NOISE FILTERING: Ignore HTTP 200/304 logs. Look ONLY for [FATAL], [ERROR], or OOM anomalies.
- SELF-CORRECTION: If your previous action returned an [ERROR], your syntax was wrong. Fix your target formatting immediately.

# EXAMPLE CASCADING FAILURE STRATEGY:
If an alert starts on 'frontend-service', you must follow the breadcrumbs:
Step 1: Run 'get_logs' on 'frontend-service'
Step 2: If frontend logs say timeout to 'payment-gateway', run 'get_logs' on 'payment-gateway'
Step 3: If gateway logs say connection refused to 'redis-cache-cluster', run 'get_logs' on 'redis-cache-cluster'
Step 4: If redis logs say cache is full, run 'flush_cache' on 'redis-cache-cluster'

Respond ONLY with valid JSON. No markdown blocks.
{"thought": "Database auth failed due to a bad deployment. I must rollback the database service.", "command": "rollback_deploy", "target": "database"}"""

    async with httpx.AsyncClient() as http:
        try:
            res = await http.post(f"{ENV_URL}/reset?task={task_name}")
            obs = res.json()["observation"]
        except Exception:
            print(f"Failed to connect to {ENV_URL}. Is server/app.py running?")
            return

        for step in range(1, 9):
            history_text = "\n".join(history[-3:]) if history else "None"
            user_prompt = f"Alert: {obs['active_alerts']}\nHealth: {obs['system_health']}%\nTerminal: {obs['terminal_output']}\nRecent History:\n{history_text}\nAction JSON:"

            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=150
                )
                action_text = completion.choices[0].message.content.strip()
                if "{" in action_text and "}" in action_text:
                    action_text = action_text[action_text.find("{"):action_text.rfind("}") + 1]
                action_json = json.loads(action_text)
                thought = action_json.get("thought", "No thought provided.")
                print(f"\n🧠 [AI THOUGHT]: {thought}")
                server_action = {"command": action_json.get("command", "error"), "target": action_json.get("target", "error")}
                error = None
            except Exception as e:
                server_action = {"command": "error", "target": "error"}
                error = "JSON Parse Error"

            try:
                step_res = await http.post(f"{ENV_URL}/step", json=server_action)
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
            history.append(f"Step {step}: ran {log_action} -> Terminal: {obs['terminal_output'][:100]}...")

            if done:
                if "system_health" in obs and obs["system_health"] > 0 and reward >= 0.90:
                    success = True  # ← FIXED: was checking == 1.0, now >= 0.90
                break

        max_possible_reward = (0.2 * (step - 1)) + 0.95
        total_reward = sum(rewards)
        score = total_reward / max_possible_reward if max_possible_reward > 0 else 0.05
        score = max(0.05, min(0.95, score))  # ← FIXED: strictly between 0 and 1
        if not success:
            score = max(0.05, score * 0.5)  # ← FIXED: never goes to 0.0

        log_end(success, step, score, rewards)

if __name__ == "__main__":
    asyncio.run(main())
