import asyncio
import httpx
import random
import time

ENV_URL = "http://127.0.0.1:7860"

CHAOS_ACTIONS = [
    {"command": "DROP TABLE users;", "target": "database"},
    {"command": "get_logs", "target": None},
    {"command": "", "target": ""},
    {"not_a_command": "get_metrics", "wrong_target": "frontend"},
    {"command": "restart_pod", "target": "auth-service-" * 100}, # Payload attack
    {"command": "rm -rf /", "target": "worker-node-1"},
    {"command": "get_metrics", "target": "127.0.0.1; ping 8.8.8.8"}, # Injection attack
    {} # Empty payload
]

async def chaos_monkey():
    print("\n==================================================")
    print(" 🐒 KUBESRE CHAOS MONKEY: STRESS TEST INITIALIZED 🐒 ")
    print("==================================================")
    
    async with httpx.AsyncClient() as http:
        # 1. Reset the environment
        try:
            res = await http.post(f"{ENV_URL}/reset?task=insane")
            print(f"[+] Env Reset Successful. Initializing Chaos Attack...")
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            return

        success_count = 0
        crash_count = 0
        
        # 2. Rapid-fire chaos
        for i in range(1, 51):
            action = random.choice(CHAOS_ACTIONS)
            try:
                # We expect the server to gracefully handle the bad JSON or return an error string
                res = await http.post(f"{ENV_URL}/step", json=action, timeout=1.0)
                
                if res.status_code in [200, 422]: 
                    # 422 is FastAPI's graceful "Validation Error". 200 is our graceful "Invalid Command"
                    success_count += 1
                    status_text = f"✅ Handled (HTTP {res.status_code})"
                else:
                    crash_count += 1
                    status_text = f"❌ Crash (HTTP {res.status_code})"
                    
            except httpx.ReadTimeout:
                crash_count += 1
                status_text = "❌ Timeout Crash"
            except Exception as e:
                crash_count += 1
                status_text = f"❌ Server Disconnected: {e}"
                
            print(f"  [Attack {i:02d}] Payload: {str(action)[:40]:<40} -> {status_text}")
            time.sleep(0.05) # Blast the server rapidly

        print("\n==================================================")
        print(" 🛡️ STRESS TEST RESULTS 🛡️ ")
        print("==================================================")
        print(f"Total Attacks Fired:  50")
        print(f"Graceful Handled:     {success_count}")
        print(f"Server Crashes:       {crash_count}")
        
        if crash_count == 0:
            print("\n🏆 VERDICT: ENTERPRISE GRADE. ZERO CRASHES.")
        else:
            print("\n⚠️ VERDICT: SERVER UNSTABLE.")
        print("==================================================\n")

if __name__ == "__main__":
    asyncio.run(chaos_monkey())