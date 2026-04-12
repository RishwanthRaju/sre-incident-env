import asyncio
import os
import json
from typing import List, Dict, Any
from openai import OpenAI
import httpx
import time


API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_URL = os.getenv("ENV_URL", "http://127.0.0.1:7860")


TASKS = ["easy", "medium", "hard", "extreme", "insane"]


SYSTEM_PROMPT = """You are an elite Site Reliability Engineer (SRE) AI Agent.
Your objective is to diagnose and resolve a critical server incident before health reaches 0%.


# AVAILABLE TOOLS & STRICT SYNTAX:
1. "get_metrics" - Target: exact service name (e.g., "auth-service", "database", "ingress-nginx")
2. "get_logs" - Target: exact service name
3. "run_top" - Target: exact node name (e.g., "worker-node-5")
4. "restart_pod" - Target: exact pod name
5. "rollback_deploy" - Target: exact service name ONLY (e.g., "database")
6. "block_ip" - Target: exact IP address
7. "kill_process" - Target: exact numerical PID
8. "flush_cache" - Target: "redis-cache-cluster"


# COGNITIVE DIRECTIVES:
- NOISE FILTERING: Ignore HTTP 200/304 logs. Look ONLY for [FATAL], [ERROR], or OOM anomalies.
- DO NOT REPEAT ACTIONS: Read your "Recent History". If you already checked logs, do not check them again on the same target.


# EXAMPLE CASCADING FAILURE STRATEGY:
If an alert starts on 'frontend-service', you must follow the breadcrumbs:
Step 1: Run 'get_logs' on 'frontend-service'
Step 2: If frontend logs say timeout to 'payment-gateway', run 'get_logs' on 'payment-gateway'
Step 3: If gateway logs say connection refused to 'redis-cache-cluster', run 'get_logs' on 'redis-cache-cluster'
Step 4: If redis logs say cache is full, run 'flush_cache' on 'redis-cache-cluster'


Respond ONLY with valid JSON. No markdown blocks.
{"thought": "Database auth failed due to a bad deployment. I must rollback the database service.", "command": "rollback_deploy", "target": "database"}"""


async def run_task(client: OpenAI, task_name: str) -> Dict[str, Any]:
    print(f"\n🚀 Starting Benchmark for Task: [{task_name.upper()}]")
    rewards = []
    history = []
    success = False
    
    async with httpx.AsyncClient() as http:
        try:
            res = await http.post(f"{ENV_URL}/reset?task={task_name}")
            obs = res.json()["observation"]
        except Exception as e:
            return {"task": task_name, "success": False, "score": 0.0, "steps": 0, "error": str(e)}
        
        for step in range(1, 9):
            history_text = "\n".join(history[-3:]) if history else "None"
            user_prompt = f"Alert: {obs['active_alerts']}\nHealth: {obs['system_health']}%\nTerminal: {obs['terminal_output']}\nRecent History:\n{history_text}\nAction JSON:"
            
            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0,
                    max_tokens=150
                )
                action_text = completion.choices[0].message.content.strip()
                if "{" in action_text and "}" in action_text:
                    action_text = action_text[action_text.find("{"):action_text.rfind("}") + 1]
                action_json = json.loads(action_text)
                thought = action_json.get("thought", "No thought provided.")
                print(f"   🧠 [Step {step} THOUGHT]: {thought[:100]}...")
                server_action = {"command": action_json.get("command", "error"), "target": action_json.get("target", "error")}
            except Exception:
                server_action = {"command": "error", "target": "error"}

            try:
                step_res = await http.post(f"{ENV_URL}/step", json=server_action)
                step_data = step_res.json()
                obs = step_data["observation"]
                reward = step_data["reward"]
                done = step_data["done"]
            except Exception:
                reward = 0.0
                done = True

            rewards.append(reward)
            history.append(f"Step {step}: ran {server_action['command']} -> Terminal: {obs['terminal_output'][:50]}...")

            if done:
                if "system_health" in obs and obs["system_health"] > 0:  # Original: > 0% health
                    success = True
                break
                
        max_possible_reward = (0.2 * (step - 1)) + 1.0 
        total_reward = sum(rewards)
        score = total_reward / max_possible_reward if max_possible_reward > 0 else 0.0
        score = max(0.0, min(1.0, score))
        # REMOVED: if not success: score = score * 0.5 
        
        print(f"   ✅ Finished [{task_name.upper()}] - Score: {score:.2f} - Success: {success}")
        return {"task": task_name, "success": success, "score": score, "steps": step}


async def main():
    if not API_KEY:
        print("ERROR: HF_TOKEN missing. Please set it in terminal.", flush=True)
        return

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    results = []
    
    print("\n==================================================")
    print(" 🚨 KUBESRE: FULL EVALUATION SUITE INITIALIZED 🚨 ")
    print("==================================================")
    
    for task in TASKS:
        result = await run_task(client, task)
        results.append(result)
        time.sleep(1) 
        
    print("\n\n===========================================================")
    print(" 📊 KUBESRE FINAL BENCHMARK SCORECARD 📊")
    print("===========================================================")
    print(f"{'TASK LEVEL':<15} | {'SUCCESS':<10} | {'SCORE':<10} | {'STEPS':<10}")
    print("-" * 57)
    
    total_score = 0
    success_count = 0
    for r in results:
        success_icon = "✅ Pass" if r['success'] else "❌ Fail"
        if r['success']: success_count += 1
        print(f"{r['task'].upper():<15} | {success_icon:<10} | {r['score']:<10.2f} | {r['steps']:<10}")
        total_score += r['score']
        
    avg_score = total_score / len(TASKS)
    win_rate = (success_count / len(TASKS)) * 100
    print("-" * 57)
    print(f"🏆 OVERALL AGENT WIN RATE: {win_rate:.1f}%")
    print(f"📈 AVERAGE NORMALIZED SCORE: {avg_score:.3f}")
    print("===========================================================")


if __name__ == "__main__":
    asyncio.run(main())
