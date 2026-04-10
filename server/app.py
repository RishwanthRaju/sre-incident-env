from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Dict
from datetime import datetime, UTC
import random

app = FastAPI(
    title="KubeSRE OpenEnv",
    description="Elite SRE simulation environment",
    version="9.0.0"
)

class AgentAction(BaseModel):
    command: str
    target: str

class EpisodeState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.task = ""
        self.system_health = 100.0
        self.terminal_output = ""
        self.done = False
        self.success = False
        self.step_count = 0
        self.max_steps = 10
        self.dynamic = {}
        self.root = {}

STATE = EpisodeState()

def now():
    return datetime.now(UTC).isoformat()

def obs():
    return {
        "system_health": STATE.system_health,
        "terminal_output": STATE.terminal_output,
        "step_count": STATE.step_count,
        "done": STATE.done
    }

def degrade():
    STATE.system_health = max(0, STATE.system_health - 15)
    if STATE.system_health == 0:
        STATE.done = True
        STATE.terminal_output = "[FATAL] System crashed"

def logs(signal):
    noise = [
        "GET /health 200",
        "cache ok",
        "worker alive",
        "metrics scrape ok",
        "cron success",
        "db pool stable"
    ]
    l = random.sample(noise, 5)
    l.insert(random.randint(1, 4), signal)
    return "\n".join(l)

# ---------------- TASKS ----------------

def easy():
    pod = f"auth-{random.randint(1000,9999)}"
    STATE.root = {"cmd": "restart_pod", "target": pod}
    STATE.dynamic = {"logs": False, "metrics": False}
    STATE.terminal_output = f"[ALERT] latency spike in {pod}"

def medium():
    STATE.root = {"cmd": "rollback_deploy", "target": "database"}
    STATE.dynamic = {"logs": False, "metrics": False}
    STATE.terminal_output = "[ALERT] db failures"

def hard():
    STATE.root = {"cmd": "restart_service", "target": "backend"}
    STATE.dynamic = {"logs": False, "frontend": False, "backend": False}
    STATE.terminal_output = "[ALERT] frontend 500 errors"

def insane():
    STATE.root = {"cmd": "flush_cache", "target": "redis"}
    STATE.dynamic = {
        "frontend": False,
        "payment": False,
        "redis": False
    }
    STATE.terminal_output = "[ALERT] checkout failing (500)"

TASKS = {
    "easy": easy,
    "medium": medium,
    "hard": hard,
    "insane": insane
}

# ---------------- ROUTES ----------------

@app.get("/", response_class=HTMLResponse)
def home():
    return "<h1>Elite OpenEnv Running</h1>"

@app.post("/reset")
def reset(task: str):
    task = task.lower().strip()
    if task not in TASKS:
        raise HTTPException(400, "invalid task")

    STATE.reset()
    STATE.task = task
    TASKS[task]()

    return {"observation": obs(), "done": False}

@app.post("/step")
def step(a: AgentAction):
    if not STATE.task:
        raise HTTPException(400, "reset first")

    if STATE.done:
        return {"observation": obs(), "reward": 0, "done": True}

    STATE.step_count += 1

    correct_cmd = STATE.root["cmd"]
    correct_target = STATE.root["target"]

    reward = 0.1

    # -------- LOGIC --------

    if a.command == "get_logs":
        if STATE.task == "insane":
            if a.target == "frontend":
                STATE.dynamic["frontend"] = True
                STATE.terminal_output = logs("timeout calling payment")
            elif a.target == "payment":
                STATE.dynamic["payment"] = True
                STATE.terminal_output = logs("connection refused redis")
            elif a.target == "redis":
                STATE.dynamic["redis"] = True
                STATE.terminal_output = logs("redis memory full")

        elif STATE.task == "hard":
            STATE.dynamic["frontend"] = True
            STATE.terminal_output = logs("frontend -> backend timeout")

        else:
            STATE.terminal_output = logs("error detected")

        reward = 0.25

    elif a.command == correct_cmd and a.target == correct_target:

        # -------- REASONING CHECK --------
        if STATE.task == "insane":
            if all(STATE.dynamic.values()):
                reward = 1.0
            else:
                reward = 0.2  # punished guessing

        elif STATE.task == "hard":
            if STATE.dynamic.get("frontend"):
                reward = 0.9
            else:
                reward = 0.3

        else:
            reward = 1.0

        STATE.done = True
        STATE.success = True
        STATE.terminal_output = "[SUCCESS] resolved"

    else:
        degrade()

    if STATE.step_count >= STATE.max_steps and not STATE.done:
        STATE.done = True
        STATE.terminal_output = "[FAILED] too many steps"

    return {
        "observation": obs(),
        "reward": float(reward),
        "done": STATE.done
    }