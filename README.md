---
title: KubeSRE Incident Env
emoji: 🚨
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
---

# KubeSRE: Autonomous SRE Incident Response Environment

Built by Rishwanth Raju for Meta PyTorch OpenEnv Hackathon 2026.

## 6 Difficulty Tiers

- easy: Pod latency spike - restart_pod
- medium: Bad DB deployment - rollback_deploy
- hard: Layer 7 DDoS - block_ip
- extreme: Java memory leak - kill_process by PID
- insane: Cascading frontend to payment to redis OOM - flush_cache
- apocalypse: Multi-region DB split-brain plus DDoS plus OOM plus Cache - multi-step

## Agent Architecture

ReAct plus Planning Phase plus Episodic Memory plus Confidence Scoring

Model: Qwen/Qwen2.5-72B-Instruct at temperature 0.0

## API

POST /reset?task=easy

POST /step

GET /state

GET /metrics

GET /analytics

## License

MIT License 2026 Rishwanth Raju
