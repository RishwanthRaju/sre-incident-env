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
    
    # Testing the Ultimate Task
    task_name = "insane"
    log_start(task=task_name, env="sre-incident-env", model=MODEL_NAME)
    
    rewards = []
    history = []
    success = False
    
    # --- UPGRADED ADVANCED PROMPT ENGINEERING ---
    system_prompt = """You are an elite Site Reliability Engineer (SRE). 
You MUST diagnose and fix the issue before server health hits 0%.
Commands: "get_metrics", "get_logs", "run_top", "restart_pod", "rollback_deploy", "block_ip", "kill_process", "flush_cache".

CRITICAL INSTRUCTIONS:
1. IGNORE NOISE: Ignore all normal HTTP 200/201/304 traffic or standard daemon processes. Act ONLY on [ERROR], [FATAL], [WARN], or OOM anomalies.
2. BREADCRUMBS: If an error mentions a downstream service (e.g., "cannot communicate with redis"), you MUST run "get_logs" on that new service.
3. EXTRACTION: If you find an attacking IP or a leaking PID, execute the mitigation command immediately.
4. DO NOT REPEAT ACTIONS: Read your "Recent History". If you already checked metrics, check logs next.

Respond ONLY with valid JSON EXACTLY like this: 
{"thought": "The frontend logs show a timeout reaching the gateway. I must check gateway logs.", "command": "get_logs", "target": "payment-gateway"}"""

    async with httpx.AsyncClient() as http:
        try:
            res = await http.post(f"{ENV_URL}/reset?task={task_name}")
            obs = res.json()["observation"]
        except Exception:
            print(f"Failed to connect to {ENV_URL}. Is server.py running?")
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
                
                server_action = {"command": action_json["command"], "target": action_json["target"]}
                error = None
            except Exception as e:
                server_action = {"command": "error", "target": "error"}
                action_text = "error"
                error = "JSON Parse Error"

            try:
                step_res = await http.post(f"{ENV_URL}/step", json=server_action)
                step_data = step_res.json()
                obs = step_data["observation"]
                reward = step_data["reward"]
                done = step_data["done"]
            except Exception:
                reward = 0.0
                done = True
                error = "Env connection failed"

            rewards.append(reward)
            
            log_action = f"{server_action['command']}('{server_action['target']}')"
            log_step(step, log_action, reward, done, error)
            
            history.append(f"Step {step}: ran {log_action} -> Terminal: {obs['terminal_output'][:100]}...")

            if done:
                if "system_health" in obs and obs["system_health"] > 0 and reward == 1.0:
                    success = True
                break
                
        # --- TRUE RL NORMALIZED GRADER ---
        max_possible_reward = (0.2 * (step - 1)) + 1.0 
        total_reward = sum(rewards)
        score = total_reward / max_possible_reward if max_possible_reward > 0 else 0.0
        score = max(0.0, min(1.0, score))
        if not success:
            score = score * 0.5 
            
        log_end(success, step, score, rewards)

if __name__ == "__main__":
    asyncio.run(main())
