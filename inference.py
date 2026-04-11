import asyncio
import os
import json
from typing import List, Optional, Dict
from openai import OpenAI
import httpx
from datetime import datetime

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_URL = os.getenv("ENV_URL", "http://127.0.0.1:7860")

def log_start(task: str) -> None:
    print(f"[START] task={task}", flush=True)

def log_step(step: int, reward: float) -> None:
    print(f"[STEP] step={step} reward={reward}", flush=True)

def log_end(task: str, score: float, steps: int) -> None:
    print(f"[END] task={task} score={score:.3f} steps={steps}", flush=True)

# 🧠 UPGRADE 1: EPISODIC MEMORY SYSTEM
# This is a cross-task memory that learns from previous incidents
# Just like a real SRE engineer who remembers what worked before
class EpisodicMemory:
    def __init__(self):
        self.memory: Dict[str, dict] = {}

    def store(self, task: str, alert: str, solution_cmd: str, solution_target: str, success: bool, steps: int):
        self.memory[task] = {
            "alert": alert,
            "solution_cmd": solution_cmd,
            "solution_target": solution_target,
            "success": success,
            "steps": steps,
            "timestamp": datetime.utcnow().isoformat()
        }

    def recall(self, current_task: str) -> str:
        if not self.memory:
            return "No previous incident memory available."
        memories = []
        for task, data in self.memory.items():
            if task != current_task:
                status = "RESOLVED" if data["success"] else "FAILED"
                memories.append(
                    f"[{status}] Task '{task}': Alert was '{data['alert'][:60]}'. "
                    f"Solution was '{data['solution_cmd']}' on '{data['solution_target']}' in {data['steps']} steps."
                )
        if not memories:
            return "No previous incident memory available."
        return "EPISODIC MEMORY (What worked before):\n" + "\n".join(memories)

async def main():
    if not API_KEY:
        print("ERROR: HF_TOKEN missing. Please set it in terminal.", flush=True)
        return

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    # 🧠 UPGRADE 2: CONFIDENCE-BASED REASONING
    # The AI must now rate its own confidence before acting
    # If confidence is low, it gathers more information first
    system_prompt = """You are an elite Site Reliability Engineer (SRE) AI Agent with a perfect incident resolution record.
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

# INCIDENT PLAYBOOK & FEW-SHOT EXAMPLES:
- HighLatency Alert: Extract pod name from alert. Use "restart_pod".
  Example: {"confidence": 0.99, "thought": "Latency on auth-service-123. Restarting pod.", "command": "restart_pod", "target": "auth-service-123"}

- DatabaseConnectionFailing Alert: Deploy is bad. Use "rollback_deploy" on "database" ONLY.
  Example: {"confidence": 0.99, "thought": "Database auth failed. Rolling back database service.", "command": "rollback_deploy", "target": "database"}

- TrafficSpike / DDoS Alert: Use "get_logs" on "ingress-nginx", find attacker IP, then "block_ip" on that IP.
  Example: {"confidence": 0.95, "thought": "Found attacking IP 64.74.35.18 in ingress logs. Blocking.", "command": "block_ip", "target": "64.74.35.18"}

- OutOfMemory Alert: Extract node name from alert. Use "run_top" on that node. Find PID of memory leak (java -jar). Use "kill_process".
  Example: {"confidence": 0.97, "thought": "OOM on worker-node-5. Found java process PID 99214. Killing.", "command": "kill_process", "target": "99214"}

- Checkout API 500 Alert: Follow logs frontend-service -> payment-gateway -> redis-cache-cluster, then "flush_cache".
  Example: {"confidence": 0.98, "thought": "Redis cache is full causing cascading failure. Flushing.", "command": "flush_cache", "target": "redis-cache-cluster"}

# CONFIDENCE SCORING RULE:
You MUST include a "confidence" score (0.0 to 1.0) in every JSON response.
- If confidence < 0.7: Run "get_logs" or "get_metrics" to gather more information first.
- If confidence >= 0.7: Execute the solution command directly.

Respond ONLY with valid JSON. Do not include markdown formatting.
{"confidence": 0.95, "thought": "Your reasoning here.", "command": "command_here", "target": "target_here"}"""

    # Running all 5 tasks
    task_names = ["easy", "medium", "hard", "extreme", "insane"]

    # Initialize the episodic memory system
    memory = EpisodicMemory()

    # Track overall performance for analytics
    all_results = []

    async with httpx.AsyncClient() as http:
        for task_name in task_names:
            log_start(task=task_name)
            rewards = []
            history = []
            success = False
            current_step = 0
            error_msg_for_prompt = ""
            last_alert = "Unknown"

            try:
                res = await http.post(f"{ENV_URL}/reset?task={task_name}", timeout=10.0)
                obs = res.json()["observation"]
                last_alert = obs.get('active_alerts', 'Unknown')
            except Exception as e:
                print(f"Failed to connect to {ENV_URL}: {e}", flush=True)
                return

            for step in range(1, 9):
                current_step = step
                history_text = "\n".join(history[-4:]) if history else "None"

                terminal_out = obs.get('terminal_output', '')
                terminal_snippet = terminal_out[-1500:] if terminal_out else "None"

                # 🧠 UPGRADE 1: Inject episodic memory into every prompt
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

                # Fault tolerance retry loop
                max_retries = 3
                server_action = {"command": "error", "target": "error"}
                for attempt in range(max_retries):
                    try:
                        completion = client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.0,
                            max_tokens=250
                        )
                        action_text = completion.choices[0].message.content.strip()
                        if "{" in action_text and "}" in action_text:
                            action_text = action_text[action_text.find("{"):action_text.rfind("}") + 1]
                        action_json = json.loads(action_text)

                        # 🧠 UPGRADE 2: Read confidence score
                        confidence = action_json.get("confidence", 1.0)
                        thought = action_json.get("thought", "No thought provided.")

                        print(f"\n🧠 [AI THOUGHT - {task_name.upper()}] (Confidence: {confidence:.0%}): {thought}", flush=True)

                        server_action = {
                            "command": action_json.get("command", "error"),
                            "target": action_json.get("target", "error")
                        }
                        error = None
                        error_msg_for_prompt = ""
                        break
                    except Exception:
                        if attempt == max_retries - 1:
                            server_action = {"command": "error", "target": "error"}
                            error_msg_for_prompt = "PREVIOUS FAILED: Invalid JSON. Output ONLY valid JSON."
                        else:
                            await asyncio.sleep(2)

                try:
                    step_res = await http.post(f"{ENV_URL}/step", json=server_action, timeout=10.0)
                    step_data = step_res.json()
                    obs = step_data["observation"]
                    reward = step_data["reward"]
                    done = step_data["done"]

                    if "[ERROR]" in obs.get('terminal_output', ''):
                        error_msg_for_prompt = "PREVIOUS FAILED: Command caused an error. Check target exact spelling."
                except Exception:
                    reward = 0.05
                    done = True

                rewards.append(reward)
                log_action = f"{server_action['command']}('{server_action['target']}')"
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

            log_end(task=task_name, score=score, steps=current_step)

            # 🧠 UPGRADE 1: Store this task result in episodic memory
            memory.store(
                task=task_name,
                alert=last_alert,
                solution_cmd=server_action["command"],
                solution_target=server_action["target"],
                success=success,
                steps=current_step
            )

            # Track result for analytics
            all_results.append({
                "task": task_name,
                "success": success,
                "score": score,
                "steps": current_step
            })

            try:
                await http.get(f"{ENV_URL}/grade/{task_name}")
            except Exception:
                pass

        # 🧠 UPGRADE 3: Print final performance analytics summary
        print("\n" + "="*60, flush=True)
        print("📊 KUBESRE AGENT PERFORMANCE ANALYTICS", flush=True)
        print("="*60, flush=True)
        total_score = 0
        wins = 0
        for r in all_results:
            status = "✅ RESOLVED" if r["success"] else "❌ FAILED"
            print(f"{r['task'].upper():<10} | {status} | Score: {r['score']:.3f} | Steps: {r['steps']}", flush=True)
            total_score += r["score"]
            if r["success"]:
                wins += 1
        avg = total_score / len(all_results) if all_results else 0
        win_rate = (wins / len(all_results)) * 100 if all_results else 0
        print("="*60, flush=True)
        print(f"🏆 WIN RATE: {win_rate:.1f}% | AVG SCORE: {avg:.3f}", flush=True)
        print("="*60, flush=True)

if __name__ == "__main__":
    asyncio.run(main())
