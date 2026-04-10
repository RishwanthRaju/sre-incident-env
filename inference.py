#!/usr/bin/env python3
import httpx
import time

BASE = "http://127.0.0.1:7860"

print("🚀 KubeSRE Agent Starting...\n")

# ---------------- RESET ----------------
r = httpx.post(f"{BASE}/reset?task=insane")
data = r.json()
obs = data["observation"]

print("🔁 Environment Reset")
print("Initial Observation:\n", obs, "\n")

# ---------------- AGENT LOOP ----------------

def decide_action(obs):
    text = obs["terminal_output"].lower()

    # --- HARD RULE-BASED REASONING ---
    if "timeout" in text or "frontend" in text:
        return {"command": "get_logs", "target": "frontend"}

    if "payment" in text:
        return {"command": "get_logs", "target": "payment"}

    if "redis" in text:
        return {"command": "get_logs", "target": "redis"}

    if "memory" in text:
        return {"command": "run_top", "target": "node"}

    # --- FINAL FIX ---
    return {"command": "flush_cache", "target": "redis"}


step = 0

while not obs["done"]:
    step += 1

    action = decide_action(obs)

    print(f"🧠 Step {step} → Action:", action)

    r = httpx.post(f"{BASE}/step", json=action)
    data = r.json()

    obs = data["observation"]

    print("📊 Observation:", obs)
    print("🎯 Reward:", data["reward"])
    print("-" * 50)

    time.sleep(0.5)

print("\n🏁 Episode Finished")