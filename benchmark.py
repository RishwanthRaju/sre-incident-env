import httpx
import statistics
import json
import time
from datetime import datetime, UTC

BASE = "http://127.0.0.1:7860"
TASKS = ["easy", "medium", "hard", "extreme", "insane"]
N_RUNS = 3

def safe_json(resp):
    try:
        return resp.json()
    except:
        return {}

def run_episode(task):
    r = httpx.post(f"{BASE}/reset?task={task}")
    data = safe_json(r)

    if "observation" not in data:
        return False, 0

    obs = data["observation"]
    steps = 0
    success = False

    seen = set()

    def decide(obs):
        text = obs["terminal_output"].lower()

        # --- FORCE INVESTIGATION FIRST ---
        if "auth" in text:
            return {"command": "get_logs", "target": "auth-service"}

        if "database" in text:
            return {"command": "get_logs", "target": "database"}

        if "traffic" in text:
            return {"command": "get_logs", "target": "ingress-nginx"}

        if "memory" in text:
            return {"command": "run_top", "target": "node"}

        if "frontend" in text:
            return {"command": "get_logs", "target": "frontend"}

        if "payment" in text:
            return {"command": "get_logs", "target": "payment"}

        if "redis" in text:
            return {"command": "get_logs", "target": "redis"}

        # --- AFTER INVESTIGATION ---
        if "redis memory" in text or "cache" in text:
            return {"command": "flush_cache", "target": "redis"}

        if "authentication failures" in text:
            return {"command": "rollback_deploy", "target": "database"}

        return {"command": "get_logs", "target": "frontend"}

    while not obs.get("done", True) and steps < 10:
        steps += 1

        action = decide(obs)
        key = (action["command"], action["target"])

        if key in seen:
            break
        seen.add(key)

        r = httpx.post(f"{BASE}/step", json=action)
        data = safe_json(r)

        if "observation" not in data:
            break

        obs = data["observation"]

        if obs.get("done") and data.get("reward", 0) > 0.9:
            success = True

        time.sleep(0.2)

    return success, steps


def run_benchmark():
    print("🏆 REAL KubeSRE BENCHMARK")
    print("=" * 60)

    results = {}

    for task in TASKS:
        print(f"\n{task.upper()}:")
        successes = 0
        steps_list = []

        for i in range(N_RUNS):
            print(f"  Run {i+1}/{N_RUNS}...", end="")

            success, steps = run_episode(task)
            steps_list.append(max(steps,1))

            if success:
                successes += 1
                print("✅")
            else:
                print("❌")

        success_rate = successes / N_RUNS

        results[task] = {
            "success_rate": success_rate,
            "avg_steps": statistics.mean(steps_list),
        }

    overall = sum(r["success_rate"] for r in results.values()) / len(results)

    print("\n" + "=" * 60)
    print(f"🎖️ OVERALL WIN RATE: {overall:.1%}")

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M")

    with open(f"KUBESRE_PROOF_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Saved proof file")


if __name__ == "__main__":
    run_benchmark()