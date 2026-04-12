---
title: KubeSRE Incident Env
emoji: 🚨
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
---

# KubeSRE Incident Response Environment

KubeSRE is a production-style SRE incident response environment for training and evaluating autonomous agents on realistic Kubernetes failures. It models escalating outages across six difficulty tiers, from single-service faults to a multi-region catastrophe. [file:355]

## Why this environment is useful

This environment is designed around real SRE-style workflows: reading logs, checking metrics, identifying noisy signals, and applying the correct remediation under time pressure. It includes dynamic randomization for pod names, IPs, PIDs, and nodes so agents cannot memorize answers and must actually reason through each episode. [file:346]

## Task progression

- **Easy:** Pod latency spike, confirm the failing auth pod and restart it. [file:355]
- **Medium:** Database credential failure, identify the bad deployment and roll it back. [file:355]
- **Hard:** Layer 7 DDoS attack, find the attacker IP in logs and block it. [file:355]
- **Extreme:** Java memory leak, inspect the node and kill the runaway PID. [file:355]
- **Insane:** Cascading microservice failure, trace frontend to payment to redis before flushing cache. [file:355]
- **Apocalypse:** Multi-region catastrophe involving split-brain, DDoS, OOM, and cache failure. [file:355]

## Environment features

- Dynamic target randomization on every reset. [file:346]
- Noise-injected logs that force anomaly detection instead of pattern memorization. [file:346]
- Shaped rewards that distinguish investigation from blind fixes. [file:346]
- Prometheus-compatible `/metrics` endpoint for observability. [file:353][file:346]
- Clear episode boundaries with health degradation and max-step limits. [file:346]

## API

- `POST /reset?task=easy`
- `POST /step`
- `GET /state`
- `GET /tasks`
- `GET /metrics`
- `GET /analytics` [file:353][file:346]

## Evaluation notes

The environment supports six tasks in total, with meaningful difficulty progression and dedicated graders for each task in `openenv.yaml`. [file:355]  
Earlier evaluation notes show full task coverage and a 100% win rate in the six-task report, while also documenting Apocalypse as the hardest coordination challenge. [file:348]

## License

MIT 2026 Rishwanth Raju
