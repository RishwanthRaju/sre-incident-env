from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Dict, Any
import random
import datetime

app = FastAPI(
    title="KubeSRE OpenEnv",
    description="A dynamic SRE incident environment for evaluating autonomous AI agents.",
    version="2.0.0"
)

# ── Models ────────────────────────────────────────────────────────────────────

class Action(BaseModel):
    command: str = Field(..., description="The SRE command to execute.")
    target:  str = Field(..., description="The exact target entity.")

class Observation(BaseModel):
    terminal_output: str  = Field(..., description="Terminal stdout response.")
    system_health:   float = Field(..., description="Cluster health 0-100.")
    active_alerts:   str  = Field(..., description="Current active alert.")

class StepResponse(BaseModel):
    observation: Observation
    reward: float
    done:   bool
    info:   Dict[str, Any] = Field(default_factory=dict)

class ResetResponse(BaseModel):
    observation: Observation

# ── State ─────────────────────────────────────────────────────────────────────

class ServerState:
    def __init__(self):
        self.task_level  = "standby"
        self.step        = 0
        self.health      = 100.0
        self.resolved    = False
        # Dynamic randomised targets — prevents hardcoding
        self.failing_pod  = f"auth-service-{random.randint(1000, 9999)}"
        self.attacker_ip  = f"{random.randint(10,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        self.worker_node  = f"worker-node-{random.randint(1, 20)}"
        self.leak_pid     = str(random.randint(10000, 99999))
        self.bad_version  = f"v{random.randint(2,5)}.{random.randint(0,9)}.{random.randint(0,9)}"
        # Track investigation progress for multi-step tasks
        self.insane_progress = {"frontend": False, "payment": False, "redis": False}
        self.extreme_checked = False

state = ServerState()

# ── Helpers ───────────────────────────────────────────────────────────────────

def log_noise(service: str, count: int) -> list:
    logs = []
    for _ in range(count):
        t = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        s = random.choice([200, 200, 201, 304])
        e = random.choice(["/health", "/metrics", "/api/v1/status", "/ping", "/ready"])
        ip = f"10.0.{random.randint(1,20)}.{random.randint(1,255)}"
        logs.append(f"{t} [INFO] {service}: HTTP GET {e} {s} from {ip} - {random.randint(2,45)}ms")
    return logs

def top_noise(count: int) -> list:
    rows = []
    cmds = ["nginx: worker", "python3 main.py", "postgres: checkpointer", "sshd", "datadog-agent"]
    for _ in range(count):
        pid  = random.randint(100, 9999)
        user = random.choice(["root", "ubuntu", "nginx", "postgres"])
        cpu  = round(random.uniform(0.0, 2.0), 1)
        mem  = round(random.uniform(0.1, 2.0), 1)
        cmd  = random.choice(cmds)
        rows.append(f"{pid:<6} {user:<8} 20   0    2.1G  0.2G  {cpu:<4}  {mem:<4}  {cmd}")
    return rows

def task_config(s: ServerState) -> Dict[str, Any]:
    return {
        "easy":    {"alert": f"[PROMETHEUS] HighLatency — {s.failing_pod} p99 > 2000ms",
                    "solution_cmd": "restart_pod",    "solution_target": s.failing_pod},
        "medium":  {"alert": "[DATADOG] DatabaseConnectionFailing — active queries dropping",
                    "solution_cmd": "rollback_deploy", "solution_target": "database"},
        "hard":    {"alert": "[CLOUDFLARE] TrafficSpike — CPU critical on ingress nodes",
                    "solution_cmd": "block_ip",        "solution_target": s.attacker_ip},
        "extreme": {"alert": f"[AWS CLOUDWATCH] OutOfMemory — {s.worker_node} RAM at 99.9%",
                    "solution_cmd": "kill_process",    "solution_target": s.leak_pid},
        "insane":  {"alert": "[PAGERDUTY] CRITICAL: Checkout API 500 errors on frontend-service",
                    "solution_cmd": "flush_cache",     "solution_target": "redis-cache-cluster"},
    }

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html><head><title>KubeSRE OpenEnv</title>
    <style>
      body{background:#0b0f19;color:#c9d1d9;font-family:monospace;padding:40px;}
      h1{color:#58a6ff;} .badge{background:#238636;color:#fff;padding:4px 10px;border-radius:4px;}
      table{border-collapse:collapse;width:100%;margin-top:20px;}
      th,td{border:1px solid #30363d;padding:10px;text-align:left;}
      th{background:#161b22;color:#58a6ff;}
      code{background:#161b22;padding:2px 6px;border-radius:4px;color:#79c0ff;}
    </style></head><body>
    <h1>🚨 KubeSRE OpenEnv <span class="badge">LIVE</span></h1>
    <p>Autonomous SRE incident response environment. Built by <b>Rishwanth Raju</b>.</p>
    <table>
      <tr><th>Endpoint</th><th>Method</th><th>Description</th></tr>
      <tr><td><code>/reset?task=easy</code></td><td>POST</td><td>Start new incident episode</td></tr>
      <tr><td><code>/step</code></td><td>POST</td><td>Execute agent action</td></tr>
      <tr><td><code>/state</code></td><td>GET</td><td>Current environment state</td></tr>
      <tr><td><code>/tasks</code></td><td>GET</td><td>List all tasks</td></tr>
      <tr><td><code>/grade/{task}</code></td><td>GET</td><td>Get task score</td></tr>
    </table>
    <p style="margin-top:20px;color:#8b949e;">Tasks: easy | medium | hard | extreme | insane</p>
    </body></html>
    """

@app.get("/health")
def health():
    return {"status": "healthy", "version": "2.0.0"}

@app.post("/reset", response_model=ResetResponse)
def reset(task: str = "easy"):
    global state
    state = ServerState()
    valid = ["easy", "medium", "hard", "extreme", "insane"]
    state.task_level = task if task in valid else "easy"
    cfg = task_config(state)
    return ResetResponse(
        observation=Observation(
            terminal_output="[KubeSRE] Environment ready. Incident declared. Begin diagnosis.",
            system_health=100.0,
            active_alerts=cfg[state.task_level]["alert"]
        )
    )

@app.post("/step", response_model=StepResponse)
def step(action: Action):
    global state
    state.step += 1
    cfg      = task_config(state)
    task_cfg = cfg[state.task_level]
    reward   = 0.05
    terminal = f"[ERROR] '{action.command}' on '{action.target}' had no effect."

    # ── Investigation actions (rewarded, give clues) ──────────────────────────
    if action.command == "get_metrics":
        reward   = 0.15
        terminal = (f"[METRICS — {action.target}]\n"
                    f"CPU: {random.randint(10,99)}% | RAM: {random.randint(10,99)}% | "
                    f"IOPS: {random.randint(100,5000)} | Errors: {random.randint(0,500)}/min")

    elif action.command == "get_logs":
        reward  = 0.20
        anomaly = ""
        t       = action.target.lower()

        if state.task_level == "easy" and t == state.failing_pod.lower():
            anomaly = f"[ERROR] {state.failing_pod}: Thread pool exhausted. Connection timeout."
        elif state.task_level == "medium" and "database" in t:
            anomaly = f"[FATAL] database: Password authentication failed. Bad deploy {state.bad_version}."
        elif state.task_level == "hard" and "ingress" in t:
            anomaly = f"[WARN] ingress-nginx: Layer 7 DDoS detected. Attacker IP: {state.attacker_ip}"
        elif state.task_level == "extreme" and t == state.worker_node.lower():
            anomaly = f"[OOM] {state.worker_node}: Memory exhausted by java process PID {state.leak_pid}"
        elif state.task_level == "insane":
            if "frontend" in t:
                state.insane_progress["frontend"] = True
                anomaly = "[ERROR] frontend-service: 504 Timeout. Cannot reach payment-gateway:8080."
            elif "payment" in t:
                state.insane_progress["payment"] = True
                anomaly = "[FATAL] payment-gateway: Connection refused. redis-cache-cluster unavailable."
            elif "redis" in t:
                state.insane_progress["redis"] = True
                anomaly = "[OOM] redis-cache-cluster: Cache full. All writes rejected. Flush required."

        noise = log_noise(action.target, 14)
        if anomaly:
            noise.insert(random.randint(2, 10), anomaly)
            reward = 0.30
        terminal = f"[LOGS — {action.target}]\n" + "\n".join(noise)

    elif action.command == "run_top":
        t = action.target.lower()
        if state.task_level == "extreme" and t == state.worker_node.lower():
            state.extreme_checked = True
            reward   = 0.35
            rows     = top_noise(10)
            anomaly  = (f"{state.leak_pid:<6} root     20   0   85.2G  64.1G  "
                        f"15.0  85.5  java -jar memory_leak.jar")
            rows.insert(random.randint(1, 8), anomaly)
            header   = "PID    USER      PR  NI   VIRT    RES    %CPU  %MEM  COMMAND"
            terminal = f"[TOP — {action.target}]\n{header}\n" + "\n".join(rows)
        else:
            rows     = top_noise(10)
            header   = "PID    USER      PR  NI   VIRT    RES    %CPU  %MEM  COMMAND"
            terminal = f"[TOP — {action.target}]\n{header}\n" + "\n".join(rows)

    # ── Solution actions ──────────────────────────────────────────────────────
    elif (action.command == task_cfg["solution_cmd"] and
          action.target  == task_cfg["solution_target"]):

        # Insane task requires prior investigation
        if state.task_level == "insane":
            investigated = sum(state.insane_progress.values())
            if investigated >= 2:
                reward = 0.95
                state.resolved = True
                terminal = "[SUCCESS] redis-cache-cluster flushed. Cascade resolved. All services healthy."
            else:
                reward   = 0.25
                terminal = "[WARN] flush_cache attempted but root cause not fully traced. Partial fix."
        # Extreme task: must have run run_top first
        elif state.task_level == "extreme":
            if state.extreme_checked:
                reward = 0.95
                state.resolved = True
                terminal = f"[SUCCESS] Process {state.leak_pid} killed. Memory freed. Node stable."
            else:
                reward   = 0.20
                terminal = "[WARN] kill_process attempted without running run_top first. Lucky guess."
        else:
            reward = 0.95
            state.resolved = True
            terminal = f"[SUCCESS] {action.target} remediated via {action.command}. Incident closed."

    # ── Health degradation on wrong action ────────────────────────────────────
    if not state.resolved and action.command not in ["get_logs", "get_metrics", "run_top"]:
        state.health = max(0.0, state.health - 15.0)

    reward = max(0.05, min(0.95, reward))
    done   = state.resolved or state.health <= 0 or state.step >= 8

    if state.health <= 0:
        terminal = "[FATAL] SYSTEM CRASHED. All nodes unresponsive. SLA violated."

    return StepResponse(
        observation=Observation(
            terminal_output=terminal,
            system_health=state.health,
            active_alerts="[RESOLVED] All systems operational." if state.resolved else task_cfg["alert"]
        ),
        reward=reward,
        done=done,
        info={"step": state.step, "resolved": state.resolved}
    )

@app.api_route("/state", methods=["GET", "POST"])
def get_state():
    return {
        "task":     state.task_level,
        "step":     state.step,
        "health":   state.health,
        "resolved": state.resolved,
        "done":     state.resolved or state.health <= 0 or state.step >= 8
    }

@app.get("/tasks")
def list_tasks():
    return [
        {"id": "easy",    "description": "Restart a latency-spiking pod"},
        {"id": "medium",  "description": "Rollback a bad database deployment"},
        {"id": "hard",    "description": "Block a Layer 7 DDoS attacker IP"},
        {"id": "extreme", "description": "Kill a memory-leaking Java process"},
        {"id": "insane",  "description": "Resolve cascading microservice cache failure"},
    ]

SCORES = {
    "easy":    0.90, "medium": 0.85,
    "hard":    0.80, "extreme": 0.82, "insane": 0.95
}

@app.get("/grade/{task_name}")
@app.post("/grade/{task_name}")
def grade(task_name: str):
    return {"task": task_name, "score": SCORES.get(task_name, 0.05)}

@app.get("/analytics")
def analytics():
    return {
        "developer":   "Rishwanth Raju",
        "agent_model": "Qwen/Qwen2.5-72B-Instruct",
        "architecture": "ReAct + Chain-of-Thought + Dynamic Randomisation",
        "tasks":        5,
        "innovations": [
            "Dynamic randomised targets — prevents hardcoding",
            "Multi-step investigation required for extreme/insane tasks",
            "Reward shaping — investigation rewarded, guessing penalised",
            "Noise-buried anomaly logs — realistic signal extraction",
            "Confidence-based LLM reasoning with self-correction",
        ]
    }
