from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import random

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
    command: str = Field(..., description="The terminal command to execute (e.g., 'get_logs', 'block_ip').")
    target: str = Field(..., description="The target entity (e.g., 'auth-service', '10.0.0.99', 'redis-cache-cluster').")

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
        terminal_out = f"[SYSTEM METRICS - {action.target}]\nCPU: {random.randint(10,99)}% | RAM: {random.randint(10,99)}%"
        
    elif action.command == "get_logs":
        reward += 0.20
        if state.task_level == "easy" and action.target == state.failing_pod:
            terminal_out = f"[ERROR] {state.failing_pod}: Timeout connecting. Thread pool exhausted."
        elif state.task_level == "medium" and action.target == "database":
            terminal_out = f"[FATAL] Password auth failed. Hint: Bad credentials in deployment {state.bad_version}."
        elif state.task_level == "hard" and "ingress" in action.target:
            terminal_out = f"[WARN] ingress-nginx: Layer 7 DDoS attack from {state.attacker_ip}."
        elif state.task_level == "insane":
            if action.target == "frontend-service":
                terminal_out = "[ERROR] frontend-service: 504 Gateway Timeout. Failed to reach 'payment-gateway' on port 8080."
            elif action.target == "payment-gateway":
                terminal_out = "[FATAL] payment-gateway: Connection refused. Cannot communicate with 'redis-cache-cluster'. State is corrupted."
            elif action.target == "redis-cache-cluster":
                terminal_out = "[OOM] redis-cache-cluster: Cache memory is full. Cannot accept writes. Requires command 'flush_cache'."
            else:
                terminal_out = f"[LOGS] No errors found for {action.target}."
        else:
            terminal_out = f"[LOGS] No anomalous logs found for {action.target}."
            
    elif action.command == "run_top":
        if state.task_level == "extreme" and action.target == state.worker_node:
            reward += 0.30
            terminal_out = f"PID   USER  %CPU  %MEM  COMMAND\n{state.leak_pid} root  15.0  85.5  java -jar memory_leak.jar\n1     root  0.1   0.2   systemd"
        else:
            terminal_out = f"[TOP] Normal processes running on {action.target}."

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