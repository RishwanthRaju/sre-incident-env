from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any
import random
import datetime

app = FastAPI(
    title="KubeSRE OpenEnv",
    description="A dynamic, time-sensitive environment for testing SRE AI Agents.",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "✅ KubeSRE Dynamic Environment is Live! Available endpoints: /reset, /step, /state"}

# --- ENTERPRISE-GRADE OPENENV MODELS ---
class Action(BaseModel):
    command: str = Field(..., description="The terminal command to execute.")
    target: str = Field(..., description="The target entity.")

class Observation(BaseModel):
    terminal_output: str = Field(..., description="The simulated stdout terminal response.")
    system_health: float = Field(..., description="Current cluster health (0.0 to 100.0). Drops over time.")
    active_alerts: str = Field(..., description="The live PagerDuty/Prometheus alert string.")

class StepResponse(BaseModel):
    observation: Observation
    reward: float = Field(..., description="Continuous reward signal between 0.0 and 1.0")
    done: bool = Field(..., description="True if incident resolved or system crashed.")
    info: Dict[str, Any] = Field(default_factory=dict, description="Metadata including step count.")

class ResetResponse(BaseModel):
    observation: Observation

# --- Dynamic State Management ---
class ServerState:
    def __init__(self):
        self.task_level = "easy"
        self.step = 0
        self.health = 100.0
        self.resolved = False
        
        self.attacker_ip = f"{random.randint(10,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        self.failing_pod = f"auth-service-{random.randint(1000,9999)}"
        self.bad_version = f"v{random.randint(2,5)}.{random.randint(0,9)}.{random.randint(0,9)}"
        self.cpu_spike = random.uniform(98.0, 100.0)
        self.worker_node = f"worker-node-{random.randint(1, 20)}"
        self.leak_pid = str(random.randint(10000, 99999))

state = ServerState()

# --- NOISE GENERATORS (THE NEEDLE IN A HAYSTACK) ---
def generate_log_noise(service: str, count: int) -> list:
    logs = []
    for _ in range(count):
        time_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        status = random.choice([200, 200, 201, 304])
        endpoint = random.choice(["/health", "/metrics", "/api/v1/status", "/ping", "/ready"])
        ip = f"10.0.{random.randint(1,20)}.{random.randint(1,255)}"
        logs.append(f"{time_str} [INFO] {service}: HTTP GET {endpoint} {status} from {ip} - {random.randint(2,45)}ms")
    return logs

def generate_top_noise(count: int) -> list:
    processes = []
    users = ["root", "ubuntu", "nginx", "postgres", "datadog"]
    cmds = ["nginx: worker process", "python3 main.py", "postgres: checkpointer", "sshd: /usr/sbin/sshd", "agent"]
    for _ in range(count):
        pid = random.randint(100, 9999)
        user = random.choice(users)
        cpu = round(random.uniform(0.0, 1.5), 1)
        mem = round(random.uniform(0.1, 2.0), 1)
        cmd = random.choice(cmds)
        processes.append(f"{pid:<6} {user:<8} 20   0    2.1G    0.2G   0.0G  {cpu:<4}  {mem:<4}  {cmd}")
    return processes

def get_dynamic_tasks(s: ServerState) -> Dict[str, Any]:
    return {
        "easy": {
            "alert": f"[PROMETHEUS] HighLatency - {s.failing_pod} p99 > 2000ms",
            "solution_cmd": "restart_pod",
            "solution_target": s.failing_pod
        },
        "medium": {
            "alert": "[DATADOG] DatabaseConnectionFailing - Active queries dropping",
            "solution_cmd": "rollback_deploy",
            "solution_target": "database"
        },
        "hard": {
            "alert": "[CLOUDFLARE] TrafficSpike - CPU critical on ingress nodes",
            "solution_cmd": "block_ip",
            "solution_target": s.attacker_ip
        },
        "extreme": {
            "alert": f"[AWS CLOUDWATCH] OutOfMemory - {s.worker_node} RAM at 99.9%",
            "solution_cmd": "kill_process",
            "solution_target": s.leak_pid
        },
        "insane": {
            "alert": "[PAGERDUTY] CRITICAL: Checkout API is throwing 500 errors on 'frontend-service'",
            "solution_cmd": "flush_cache",
            "solution_target": "redis-cache-cluster"
        }
    }

@app.post("/reset", response_model=ResetResponse)
def reset(task: str = "hard"):
    global state
    state = ServerState() 
    state.task_level = task if task in ["easy", "medium", "hard", "extreme", "insane"] else "easy"
    tasks = get_dynamic_tasks(state)
    return ResetResponse(
        observation=Observation(
            terminal_output="[KubeSRE Terminal] Connected. Waiting for commands.",
            system_health=state.health,
            active_alerts=tasks[state.task_level]["alert"]
        )
    )

@app.post("/step", response_model=StepResponse)
def step(action: Action):
    global state
    state.step += 1
    tasks = get_dynamic_tasks(state)
    task_info = tasks[state.task_level]
    
    if not state.resolved:
        state.health -= 15.0 

    reward = 0.0
    terminal_out = f"Command '{action.command}' executed on '{action.target}'. No immediate resolution."
    
    if action.command == "get_metrics":
        reward += 0.15
        terminal_out = f"[SYSTEM METRICS - {action.target}]\nCPU: {random.randint(10,99)}% | RAM: {random.randint(10,99)}% | IOPS: {random.randint(100,5000)}"
        
    elif action.command == "get_logs":
        reward += 0.20
        anomaly_log = ""
        if state.task_level == "easy" and action.target == state.failing_pod:
            anomaly_log = f"[ERROR] {state.failing_pod}: Timeout connecting. Thread pool exhausted."
        elif state.task_level == "medium" and action.target == "database":
            anomaly_log = f"[FATAL] Password auth failed. Hint: Bad credentials in deployment {state.bad_version}."
        elif state.task_level == "hard" and "ingress" in action.target:
            anomaly_log = f"[WARN] ingress-nginx: Layer 7 DDoS attack from {state.attacker_ip}."
        elif state.task_level == "insane":
            if action.target == "frontend-service":
                anomaly_log = "[ERROR] frontend-service: 504 Gateway Timeout. Failed to reach 'payment-gateway' on port 8080."
            elif action.target == "payment-gateway":
                anomaly_log = "[FATAL] payment-gateway: Connection refused. Cannot communicate with 'redis-cache-cluster'."
            elif action.target == "redis-cache-cluster":
                anomaly_log = "[OOM] redis-cache-cluster: Cache memory is full. Cannot accept writes. Requires command 'flush_cache'."
        
        # HIDE THE ANOMALY IN 15 LINES OF NOISE
        noise = generate_log_noise(action.target, 15)
        if anomaly_log:
            insert_idx = random.randint(2, 12)
            noise.insert(insert_idx, anomaly_log)
        terminal_out = f"[RAW SYSTEM LOGS - {action.target}]\n" + "\n".join(noise)
            
    elif action.command == "run_top":
        if state.task_level == "extreme" and action.target == state.worker_node:
            reward += 0.30
            noise = generate_top_noise(12)
            anomaly_top = f"{state.leak_pid:<6} root     20   0    85.2G   64.1G  2.1G  15.0  85.5  java -jar memory_leak.jar"
            insert_idx = random.randint(1, 10)
            noise.insert(insert_idx, anomaly_top)
            header = "PID    USER      PR   NI   VIRT    RES    SHR   %CPU  %MEM  COMMAND"
            terminal_out = f"[TOP OUTPUT - {action.target}]\n{header}\n" + "\n".join(noise)
        else:
            noise = generate_top_noise(12)
            header = "PID    USER      PR   NI   VIRT    RES    SHR   %CPU  %MEM  COMMAND"
            terminal_out = f"[TOP OUTPUT - {action.target}]\n{header}\n" + "\n".join(noise)

    elif action.command == task_info["solution_cmd"] and action.target == task_info["solution_target"]:
        state.resolved = True
        state.health = 100.0
        reward += 1.0
        terminal_out = f"[SUCCESS] Root cause mitigated. {action.target} stabilized. Incident closed."
        
    else:
        reward -= 0.1
        terminal_out = f"[ERROR] Action '{action.command}' on '{action.target}' failed. Health continues to drop."

    reward = max(0.0, min(1.0, reward))
    done = state.resolved or state.health <= 0 or state.step >= 8
    
    if state.health <= 0:
        terminal_out = "[FATAL] SYSTEM CRASHED. All nodes unresponsive."

    obs = Observation(
        terminal_output=terminal_out,
        system_health=state.health,
        active_alerts="[RESOLVED] All systems operational." if state.resolved else task_info["alert"]
    )
    
    return StepResponse(observation=obs, reward=reward, done=done, info={"step": state.step})

@app.api_route("/state", methods=["GET", "POST"])
def get_state():
    return {"step": state.step, "health": state.health, "resolved": state.resolved, "task": state.task_level}

def main():
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("server.app:app", host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
