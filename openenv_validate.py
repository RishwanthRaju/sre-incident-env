#!/usr/bin/env python3
import requests
import json
import time

def validate_openenv():
    try:
        time.sleep(2)
        resp = requests.post('http://127.0.0.1:7860/reset?task=easy', timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert 'observation' in data
        assert data['done'] is False
        print('✅ OpenEnv Reset (POST OK)')
        return True
    except Exception as e:
        print(f'❌ OpenEnv Reset failed: {e}')
        return False

if __name__ == '__main__':
    print('Testing OpenEnv endpoints...')
    validate_openenv()
