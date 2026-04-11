---
title: KubeSRE Incident Env
emoji: 🚨
colorFrom: red
colorTo: orange
sdk: docker
pinned: false
---

# 🚨 KubeSRE: Autonomous SRE Incident Response Environment

Built by **Rishwanth Raju** for the Meta PyTorch OpenEnv Hackathon 2026.

An OpenEnv-compatible, production-grade environment where autonomous AI agents diagnose and resolve cascading Kubernetes infrastructure failures under time pressure.

## What Makes This Different

Most environments let agents brute-force the answer. KubeSRE does not.

- Temporal Degradation: -15% health per wrong fix — forces efficient reasoning
- Dynamic Randomisation: Pod names, IPs, PIDs, nodes change every reset
- Noise-Buried Signals: Anomaly hidden among 14 realistic log lines
- Multi-Step Reasoning: Insane task requires tracing 3-service cascade
- Dedup Penalty: Repeating same action costs -5% health

## 5 Difficulty Tiers

- easy: Pod latency spike — restart_pod
- medium: Bad DB deployment — rollback_deploy
- hard: Layer 7 DDoS — block_ip
- extreme: Java memory leak — kill_process by PID
- insane: Cascading frontend → payment → redis OOM — flush_cache

## Agent Architecture

ReAct + Episodic Memory + Confidence Scoring + Self-Correction

Model: Qwen/Qwen2.5-72B-Instruct at temperature=0.0

## API

POST /reset?task=easy — Start episode

POST /step — Execute action

GET /state — Current state

GET /tasks — List tasks

GET /grade/{task} — Task score

GET /analytics — Agent analytics

## License

MIT License 2026 Rishwanth Raju
