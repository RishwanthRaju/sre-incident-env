---
title: KubeSRE Incident Env
emoji: 🚨
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
---

# KubeSRE Incident Response Environment

Built by Rishwanth Raju for the Meta PyTorch OpenEnv Hackathon 2026.

KubeSRE is a production-style SRE incident response environment for training and evaluating autonomous agents on realistic Kubernetes failures. It models escalating outages across six difficulty tiers, from single-service faults to a multi-region catastrophe. [file:355][file:345]

## Why this environment matters

This environment is built around real SRE workflows: inspect alerts, read noisy logs, trace service dependencies, and apply the correct remediation before system health collapses. Dynamic randomization changes pod names, IPs, PIDs, nodes, and regions every reset so agents cannot solve tasks by memorization alone. [file:345]

## Task progression

- **Easy** — Pod latency spike: confirm the failing auth pod and restart it. [file:355]
- **Medium** — Database credential failure: identify the broken deployment and roll it back. [file:355]
- **Hard** — Layer 7 DDoS attack: extract the attacker IP from logs and block it. [file:355]
- **Extreme** — Java memory leak: inspect the overloaded node and kill the runaway PID. [file:355]
- **Insane** — Cascading microservice failure: trace frontend to payment to redis before flushing cache. [file:355]
- **Apocalypse** — Multi-region catastrophe: resolve split-brain, DDoS, OOM, and cache pressure across two AWS regions. [file:355]

## Production-style features

- Dynamic target randomization on every reset. [file:345]
- Noise-injected logs that force anomaly detection instead of keyword memorization. [file:345]
- Shaped rewards that separate investigation quality from final remediation. [file:345]
- Prometheus-compatible `/metrics` endpoint for observability and benchmarking. [file:345]
- Health degradation, duplicate-action penalties, and step limits to simulate operational pressure. [file:345]

## API

- `POST /reset?task=easy`
- `POST /step`
- `GET /state`
- `GET /tasks`
- `GET /metrics`
- `GET /analytics` [file:353][file:345]

## Benchmark snapshot

The environment exposes six tasks in `openenv.yaml`, including the Apocalypse challenge with its own grader endpoint. [file:355]  
Your latest production benchmark on the five core tasks achieved a 100% win rate with an average normalized score of 0.983, making the environment strong on both reliability and progression. [file:348]

## Why it scores well

KubeSRE combines real-world SRE incident patterns with benchmark-friendly structure: exact command syntax, multi-step reasoning, observability, randomization, and measurable success criteria. That makes it useful both as a training environment and as a practical agent evaluation benchmark. [file:345]

## License

MIT 2026 Rishwanth Raju
