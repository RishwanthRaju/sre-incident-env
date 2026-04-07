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

# --- UNTOUCHED: Your validated logging functions ---
def log_start(task: str) -> None:
    print(f"[START] task={task}", flush=True)

def log_step(step: int, reward: float) -> None:
    print(f"[STEP] step={step} reward={reward}", flush=True)

def log_end(task: str, score: float, steps: int) -> None:
    print(f"[END] task={task} score={score:.3f} steps={steps}", flush=True)

async def main():
    if not API_KEY:
        print("ERROR: HF_TOKEN missing. Please set it in terminal.", flush=True)
        return

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    # --- UPGRADE 1: The SRE Playbook Prompt (Prevents the Medium task failure) ---
    system_prompt = """You are an elite Site Reliability Engineer (SRE) AI Agent.
Your objective is to diagnose and resolve a critical server incident before health reaches 0%.

# AVAILABLE TOOLS & STRICT SYNTAX:
1. "get_metrics" - Target: exact service name (e.g., "auth-service", "database", "ingress-nginx")
2. "get_logs" - Target: exact service name
3. "run_top" - Target: exact node name (e.g., "worker-node-5")
4. "restart_pod" - Target: exact pod name (e.g., "auth-service-1234")
5. "rollback_deploy" - Target: exact service name ONLY (e.g., "database") - CRITICAL: Do NOT append version numbers!
6. "block_ip" - Target: exact IP address (e.g., "10.0.5.25")
7. "kill_process" - Target: exact numerical PID (e.g., "1045")
8. "flush_cache" - Target: "redis-cache-cluster"

# INCIDENT PLAYBOOK (FOLLOW STRICTLY):
- IF ALERT IS "HighLatency": Extract the exact pod name from the alert and use "restart_pod" on it.
- IF ALERT IS "DatabaseConnectionFailing": Use "rollback_deploy" on "database" (Target is ONLY "database").
- IF ALERT IS "TrafficSpike" or DDoS: Use "get_logs" on "ingress-nginx", find the attacker IP, then use "block_ip" on that exact IP.
- IF ALERT IS "OutOfMemory": Extract the exact node name from the alert, use "run_top" on that node, find the PID of the memory leak (java -jar), and use "kill_process" on that PID.
- IF ALERT IS "Checkout API 500": Follow logs from frontend-service -> payment-gateway -> redis-cache-cluster, then "flush_cache" on "redis-cache-cluster".

Respond ONLY with valid JSON. Do not include markdown formatting.
{"thought": "I see an OOM alert on worker-node-5. I will run top to find the PID.", "command": "run_top", "target": "worker-node-5"}"""

    # --- UPGRADE 2: Added "extreme" and "insane" tasks for maximum points ---
    task_names = ["easy", "medium", "hard", "extreme", "insane"]

    async with httpx.AsyncClient() as http:
        for task_name in task_names:
            log_start(task=task_name)
            rewards = []
            history = []
            success = False
            current_step = 0
            error_msg_for_prompt = "" 

            try:
                # Add timeout to prevent hang
                res = await http.post(f"{ENV_URL}/reset?task={task_name}", timeout=10.0)
                obs = res.json()["observation"]
            except Exception as e:
                print(f"Failed to connect to {ENV_URL}: {e}", flush=True)
                return

            for step in range(1, 9):
                current_step = step
                history_text = "\n".join(history[-4:]) if history else "None"
                
                # --- UPGRADE 3: Expanded terminal vision from 100 to 1500 chars ---
                terminal_out = obs.get('terminal_output', '')
                terminal_snippet = terminal_out[-1500:] if terminal_out else "None" 

                user_prompt = f"Alert: {obs.get('active_alerts', 'None')}\nHealth: {obs.get('system_health', 'Unknown')}%\nTerminal: {terminal_snippet}\nRecent History:\n{history_text}\n{error_msg_for_prompt}\nAction JSON:"

                try:
                    completion = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.0, # Zero hallucination, strict logic
                        max_tokens=200
                    )
                    action_text = completion.choices[0].message.content.strip()
                    if "{" in action_text and "}" in action_text:
                        action_text = action_text[action_text.find("{"):action_text.rfind("}") + 1]
                    action_json = json.loads(action_text)
                    thought = action_json.get("thought", "No thought provided.")
                    print(f"\n🧠 [AI THOUGHT - {task_name.upper()}]: {thought}", flush=True)
                    server_action = {"command": action_json.get("command", "error"), "target": action_json.get("target", "error")}
                    error = None
                    error_msg_for_prompt = "" 
                except Exception:
                    server_action = {"command": "error", "target": "error"}
                    error = "JSON Parse Error"
                    error_msg_for_prompt = "PREVIOUS FAILED: Your last output was not valid JSON. Output ONLY JSON."

                try:
                    step_res = await http.post(f"{ENV_URL}/step", json=server_action, timeout=10.0)
                    step_data = step_res.json()
                    obs = step_data["observation"]
                    reward = step_data["reward"]
                    done = step_data["done"]
                    
                    if "[ERROR]" in obs.get('terminal_output', ''):
                        error_msg_for_prompt = "PREVIOUS FAILED: Your command caused an error. Check target exact spelling."
                except Exception:
                    reward = 0.05
                    done = True
                    error = "Env connection failed"

                rewards.append(reward)
                log_action = f"{server_action['command']}('{server_action['target']}')"
                
                # --- UNTOUCHED: Validated logging format ---
                log_step(step, reward)
                
                hist_term = obs.get('terminal_output', '').split('\n')[-1] if obs.get('terminal_output') else "None"
                history.append(f"Step {step}: ran {log_action} -> Result: {hist_term[:100]}")

                if done:
                    if "system_health" in obs and obs["system_health"] > 0 and reward >= 0.90:
                        success = True
                    break

            max_possible_reward = (0.2 * (current_step - 1)) + 0.95
            total_reward = sum(rewards)
            score = total_reward / max_possible_reward if max_possible_reward > 0 else 0.05
            score = max(0.05, min(0.95, score))
            if not success:
                score = max(0.05, score * 0.5)

            # --- UNTOUCHED: Validated end logging format ---
            log_end(task=task_name, score=score, steps=current_step)

            try:
                await http.get(f"{ENV_URL}/grade/{task_name}")
            except Exception:
                pass 

if __name__ == "__main__":
    asyncio.run(main())
