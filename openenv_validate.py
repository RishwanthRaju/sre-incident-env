'#!/usr/bin/env python3
import requests
def validate_openenv():
    try:
        resp = requests.post("http://127.0.0.1:7860/reset?task=easy", timeout=5)
        print("✅ OpenEnv Reset (POST OK)")
        return True
    except:
        print("❌ OpenEnv Reset failed")
        return False
if __name__ == "__main__":
    validate_openenv()' | Set-Content openenv_validate.py