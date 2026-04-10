from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC
import random
import re

app = FastAPI(
    title="KubeSRE OpenEnv",
    description="A dynamic, time-sensitive environment for testing SRE AI Agents.",
    version="2.0.0"
)


class AgentAction(BaseModel):
    command: str = Field(..., description="Command/tool selected by the agent")
    target: str = Field(..., description="Exact target for the command")


class EpisodeState:
    def __init__(self) -> None:
        self.task: str = ""
        self.active_alerts: str = ""
        self.system_health: float = 100.0
        self.terminal_output: str = ""
        self.done: bool = False
        self.success: bool = False
        self.step_count: int = 0
        self.max_steps: int = 8
        self.history: List[Dict[str, Any]] = []
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None

        self.root_cause: Dict[str, Any] = {}
        self.dynamic_values: Dict[str, Any] = {}
        self.allowed_actions: Dict[str, Any] = {}
        self.seen_targets: set = set()

    def reset(self) -> None:
        self.__init__()


STATE = EpisodeState()


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def noisy_lines() -> List[str]:
    pool = [
        '127.0.0.1 - - "GET /healthz HTTP/1.1" 200',
        '127.0.0.1 - - "GET /ready HTTP/1.1" 200',
        'worker heartbeat ok',
        'background cron sync complete',
        'scheduler tick processed',
        'cache warmup completed',
        'HTTP 304 /favicon.ico',
        'HTTP 200 /metrics scrape',
        'kube-proxy routine reconciliation complete',
        'sidecar telemetry flush ok',
        'db connection pool healthy',
        'nginx keepalive check passed',
        'daemonset monitor idle',
        'pod lifecycle hook completed',
        'service mesh trace export complete',
    ]
    random.shuffle(pool)
    return pool[:10]


def build_log_blob(needle: str) -> str:
    lines = noisy_lines()
    insert_at = random.randint(2, min(8, len(lines)))
    lines.insert(insert_at, needle)
    return "\n".join(lines)


def degrade_health_if_needed(success_now: bool) -> None:
    if not success_now:
        STATE.system_health = max(0.0, STATE.system_health - 15.0)
    if STATE.system_health <= 0:
        STATE.done = True
        STATE.success = False
        STATE.terminal_output = "[FATAL] Cluster health reached 0%. Fatal crash."


def build_observation() -> Dict[str, Any]:
    return {
        "active_alerts": STATE.active_alerts,
        "system_health": round(STATE.system_health, 2),
        "terminal_output": STATE.terminal_output,
        "step_count": STATE.step_count,
        "done": STATE.done,
    }


def record_step(command: str, target: str, reward: float, note: str) -> None:
    STATE.history.append({
        "step": STATE.step_count,
        "command": command,
        "target": target,
        "reward": reward,
        "health": round(STATE.system_health, 2),
        "note": note,
        "timestamp": now_utc(),
    })


def finalize_episode(success: bool) -> None:
    STATE.done = True
    STATE.success = success
    STATE.finished_at = now_utc()


def repeated_same_action(command: str, target: str) -> bool:
    return any(h["command"] == command and h["target"] == target for h in STATE.history)


def get_episode_grade() -> Dict[str, Any]:
    optimal_steps = STATE.root_cause.get("optimal_steps", 4)
    success_bonus = 1.0 if STATE.success else 0.0
    health_score = max(0.0, STATE.system_health / 100.0)
    efficiency_score = min(1.0, optimal_steps / max(STATE.step_count, 1))
    penalty_count = sum(1 for h in STATE.history if h["reward"] < 0.1)
    penalty_factor = max(0.0, 1.0 - (0.12 * penalty_count))

    raw_score = (0.45 * success_bonus) + (0.30 * health_score) + (0.25 * efficiency_score)
    normalized_score = max(0.0, min(1.0, raw_score * penalty_factor))

    return {
        "task": STATE.task,
        "success": STATE.success,
        "steps_taken": STATE.step_count,
        "optimal_steps": optimal_steps,
        "remaining_health": round(STATE.system_health, 2),
        "penalty_count": penalty_count,
        "normalized_score": round(normalized_score, 3),
        "history": STATE.history,
        "started_at": STATE.started_at,
        "finished_at": STATE.finished_at,
    }


def setup_easy() -> None:
    pod_id = random.randint(1000, 9999)
    pod_name = f"auth-service-{pod_id}"

    STATE.active_alerts = f"[HighLatency] auth-service pod {pod_name} latency critical"
    STATE.root_cause = {
        "kind": "restart_pod",
        "pod_name": pod_name,
        "optimal_steps": 2,
    }
    STATE.dynamic_values = {
        "pod_name": pod_name,
    }
    STATE.allowed_actions = {
        "service": "auth-service",
        "pod": pod_name,
    }
    STATE.terminal_output = "Alert received. High latency detected on auth-service."


def setup_medium() -> None:
    STATE.active_alerts = "[DatabaseConnectionFailing] database auth failures spiking after bad deployment"
    STATE.root_cause = {
        "kind": "rollback_deploy",
        "service": "database",
        "optimal_steps": 1,
    }
    STATE.dynamic_values = {
        "service": "database",
    }
    STATE.allowed_actions = {
        "service": "database",
    }
    STATE.terminal_output = "Alert received. Database auth failures increasing rapidly."


def setup_hard() -> None:
    attacker_ip = f"{random.randint(11, 223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

    STATE.active_alerts = "[TrafficSpike] ingress nodes CPU critical, suspected Layer 7 DDoS"
    STATE.root_cause = {
        "kind": "block_ip",
        "ip": attacker_ip,
        "optimal_steps": 2,
    }
    STATE.dynamic_values = {
        "attacker_ip": attacker_ip,
    }
    STATE.allowed_actions = {
        "service": "ingress-nginx",
        "ip": attacker_ip,
    }
    STATE.terminal_output = "Alert received. Ingress traffic spike detected."


def setup_extreme() -> None:
    node_num = random.randint(3, 18)
    node_name = f"worker-node-{node_num}"
    pid = str(random.randint(10000, 99999))

    STATE.active_alerts = f"[OutOfMemory] {node_name} memory critical, OOM kills observed"
    STATE.root_cause = {
        "kind": "kill_process",
        "node_name": node_name,
        "pid": pid,
        "optimal_steps": 2,
    }
    STATE.dynamic_values = {
        "node_name": node_name,
        "pid": pid,
    }
    STATE.allowed_actions = {
        "node": node_name,
        "pid": pid,
    }
    STATE.terminal_output = f"Alert received. OOM detected on {node_name}."


def setup_insane() -> None:
    STATE.active_alerts = "[CheckoutAPI500] frontend-service returning HTTP 500 due to cascading downstream failure"
    STATE.root_cause = {
        "kind": "flush_cache",
        "chain": ["frontend-service", "payment-gateway", "redis-cache-cluster"],
        "cache": "redis-cache-cluster",
        "optimal_steps": 4,
    }
    STATE.dynamic_values = {
        "chain": ["frontend-service", "payment-gateway", "redis-cache-cluster"],
        "cache": "redis-cache-cluster",
    }
    STATE.allowed_actions = {
        "services": ["frontend-service", "payment-gateway", "redis-cache-cluster"],
        "cache": "redis-cache-cluster",
    }
    STATE.terminal_output = "Alert received. Checkout API returning 500 errors."


TASK_SETUP = {
    "easy": setup_easy,
    "medium": setup_medium,
    "hard": setup_hard,
    "extreme": setup_extreme,
    "insane": setup_insane,
}


@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <html>
      <head><title>KubeSRE OpenEnv</title></head>
      <body style="font-family: Arial, sans-serif; padding: 2rem;">
        <h1>KubeSRE OpenEnv</h1>
        <p>Health drops by 15% for every inefficient step. Fatal crash at 0%.</p>
        <p>Run <code>python inference.py</code> in the terminal to watch the autonomous SRE agent.</p>
      </body>
    </html>
    """


@app.post("/reset")
def reset(task: str):
    task = task.lower().strip()
    if task not in TASK_SETUP:
        raise HTTPException(status_code=400, detail=f"Unknown task '{task}'")

    STATE.reset()
    STATE.task = task
    STATE.started_at = now_utc()

    TASK_SETUP[task]()

    return {
        "message": f"Task '{task}' initialized.",
        "observation": build_observation(),
    }


@app.post("/step")
def step(action: AgentAction):
    if not STATE.task:
        raise HTTPException(status_code=400, detail="Environment not initialized. Call /reset first.")

    if STATE.done:
        return {
            "observation": build_observation(),
            "reward": 0.0,
            "done": True,
            "info": "Episode already finished."
        }

    STATE.step_count += 1

    command = action.command.strip()
    target = action.target.strip()
    success_now = False
    reward = 0.05
    note = "Inefficient or incorrect action."

    if repeated_same_action(command, target):
        reward = 0.05
        STATE.terminal_output = f"[WARN] Repeated action detected: {command}('{target}')"
        degrade_health_if_needed(False)
        record_step(command, target, reward, "Repeated action penalty")
        return {
            "observation": build_observation(),
            "reward": reward,
            "done": STATE.done,
            "info": "Repeated action penalty"
        }

    if STATE.task == "easy":
        pod_name = STATE.dynamic_values["pod_name"]

        if command == "get_metrics" and target == "auth-service":
            reward = 0.15
            note = "Metrics show latency concentrated around a single auth pod."
            STATE.terminal_output = build_log_blob(
                f"[WARN] p95 latency elevated on pod {pod_name}; upstream dependencies normal"
            )

        elif command == "get_logs" and target == "auth-service":
            reward = 0.20
            note = "Logs hint that one auth pod is unstable."
            STATE.terminal_output = build_log_blob(
                f"[ERROR] auth-service routing instability traced to pod {pod_name}"
            )

        elif command == "restart_pod" and target == pod_name:
            reward = 0.95
            note = "Correct mitigation applied."
            STATE.terminal_output = f"[SUCCESS] Restarted pod {pod_name}. Latency recovered."
            success_now = True
            finalize_episode(True)

    elif STATE.task == "medium":
        if command == "rollback_deploy" and target == "database":
            reward = 0.95
            note = "Correct rollback applied."
            STATE.terminal_output = "[SUCCESS] Rolled back database deployment. Auth failures resolved."
            success_now = True
            finalize_episode(True)

        elif command == "get_logs" and target == "database":
            reward = 0.20
            note = "Helpful reconnaissance."
            STATE.terminal_output = build_log_blob(
                "[ERROR] database authentication failures started immediately after deployment rollout"
            )

    elif STATE.task == "hard":
        attacker_ip = STATE.dynamic_values["attacker_ip"]

        if command == "get_logs" and target == "ingress-nginx":
            reward = 0.20
            note = "Logs expose attacker IP."
            STATE.terminal_output = build_log_blob(
                f"[FATAL] Layer7 flood pattern detected from {attacker_ip}"
            )

        elif command == "block_ip" and target == attacker_ip:
            reward = 0.95
            note = "Correct attacker blocked."
            STATE.terminal_output = f"[SUCCESS] Blocked attacker IP {attacker_ip}. Traffic normalized."
            success_now = True
            finalize_episode(True)

    elif STATE.task == "extreme":
        node_name = STATE.dynamic_values["node_name"]
        pid = STATE.dynamic_values["pid"]

        if command == "run_top" and target == node_name:
            reward = 0.30
            note = "Top output reveals rogue PID."
            STATE.terminal_output = "\n".join([
                "top - 14:02:11 up 10 days",
                "PID USER PR NI VIRT RES SHR S %CPU %MEM TIME+ COMMAND",
                f"{pid} root 20 0 4.2g 3.1g 1200 S 93.2 85.5 12:22.19 java -jar payment-worker.jar",
                "1221 root 20 0 125m 24m 9m S 1.0 0.5 00:00.92 sshd",
            ])

        elif command == "kill_process" and target == pid:
            reward = 0.95
            note = "Correct PID terminated."
            STATE.terminal_output = f"[SUCCESS] Killed process {pid}. Memory pressure resolved on {node_name}."
            success_now = True
            finalize_episode(True)

    elif STATE.task == "insane":
        if command == "get_logs" and target == "frontend-service":
            reward = 0.20
            note = "Frontend logs reveal downstream timeout."
            STATE.terminal_output = build_log_blob(
                "[ERROR] frontend-service timeout while calling payment-gateway"
            )

        elif command == "get_logs" and target == "payment-gateway":
            reward = 0.20
            note = "Payment logs reveal cache dependency failure."
            STATE.terminal_output = build_log_blob(
                "[ERROR] payment-gateway connection refused to redis-cache-cluster"
            )

        elif command == "get_logs" and target == "redis-cache-cluster":
            reward = 0.25
            note = "Redis logs reveal cache saturation."
            STATE.terminal_output = build_log_blob(
                "[FATAL] redis-cache-cluster maxmemory reached, writes rejected"
            )

        elif command == "flush_cache" and target == "redis-cache-cluster":
            seen_chain = {h['target'] for h in STATE.history if h['command'] == 'get_logs'}
            if "frontend-service" in seen_chain and "payment-gateway" in seen_chain:
                reward = 0.95
                note = "Correct cascade mitigation applied."
                STATE.terminal_output = "[SUCCESS] Flushed redis-cache-cluster. Checkout API recovered."
                success_now = True
                finalize_episode(True)
            else:
                reward = 0.10
                note = "Mitigation guessed too early without enough tracing."
                STATE.terminal_output = "[WARN] Cache flush attempted before tracing full cascade."

        elif command == "get_metrics" and target in {"frontend-service", "payment-gateway"}:
            reward = 0.15
            note = "Some signal, but less useful than logs."
            STATE.terminal_output = build_log_blob(
                f"[WARN] elevated error-rate observed on {target}"
            )

    if not success_now and not STATE.done:
        degrade_health_if_needed(False)

    if STATE.step_count >= STATE.max_steps and not STATE.done:
        finalize_episode(False)
        STATE.terminal_output = "[FATAL] Step limit exceeded before incident resolution."

    record_step(command, target, reward, note)

    return {
        "observation": build_observation(),
        "reward": reward,
        "done": STATE.done,
        "info": note
    }


@app.get("/grade/{task_name}")
def grade_task(task_name: str):
    if not STATE.task:
        raise HTTPException(status_code=400, detail="No active task. Call /reset first.")

    if STATE.task != task_name:
        raise HTTPException(
            status_code=400,
            detail=f"Requested grade for '{task_name}' but active task is '{STATE.task}'."
        )

    return get_episode_grade()


@app.get("/state")
def get_state():
    return {
        "task": STATE.task,
        "done": STATE.done,
        "success": STATE.success,
        "step_count": STATE.step_count,
        "system_health": STATE.system_health,
        "history": STATE.history,
        "root_cause": STATE.root_cause,
    }