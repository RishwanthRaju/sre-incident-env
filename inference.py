#!/usr/bin/env python3
import httpx
import time
import os

BASE = os.getenv("OPENENV_BASE_URL", "http://127.0.0.1:7860")
BASE = BASE.rstrip("/")

print("KubeSRE Agent Starting...\n")

def decide_action(obs):
    text = obs["terminal_output"].lower()
    if "timeout" in text or "frontend" in text:
        return {"command": "get_logs", "target": "frontend"}
    if "payment" in text:
        return {"command": "get_logs", "target": "payment"}
    if "redis" in text or "memory" in text:
        return {"command": "get_logs", "target": "redis"}
    if "latency" in text or "auth" in text:
        return {"command": "restart_pod", "target": obs["terminal_output"].split()[-1]}
    if "db" in text or "database" in text:
        return {"command": "rollback_deploy", "target": "database"}
    if "backend" in text:
        return {"command": "restart_service", "target": "backend"}
    return {"command": "flush_cache", "target": "redis"}

for task in ["easy", "medium", "hard", "insane"]:
    print(f"\n{'='*50}")
    print(f"Running task: {task}")
    print('='*50)

    try:
        r = httpx.post(f"{BASE}/reset?task={task}", timeout=30)
        data = r.json()
        obs = data["observation"]
        print("Reset OK. Observation:", obs)

        step = 0
        while not obs["done"] and step < 15:
            step += 1
            action = decide_action(obs)
            print(f"Step {step} -> Action: {action}")

            r = httpx.post(f"{BASE}/step", json=action, timeout=30)
            data = r.json()
            obs = data["observation"]

            print(f"[STEP] step={step} reward={data['reward']} done={data['done']}")
            print(f"terminal: {obs['terminal_output']}")
            time.sleep(0.3)

        print(f"[END] Task {task} finished. done={obs['done']}")

    except Exception as e:
        print(f"[ERROR] Task {task} failed: {e}")

print("\nAll tasks done.")