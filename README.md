---
title: KubeSRE Incident Env
emoji: robot
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
---

# KubeSRE Autonomous SRE Incident Response Environment

Built by Rishwanth Raju for Meta PyTorch OpenEnv Hackathon 2026.

Production-grade OpenEnv-compatible environment where autonomous AI agents
diagnose and resolve cascading Kubernetes infrastructure failures under
real-time pressure. 6 difficulty tiers, dynamic randomised targets,
Prometheus metrics, and enforced multi-step reasoning.

## What Makes KubeSRE Stand Out

Temporal Degradation: -15% health per wrong fix forces efficient reasoning.

Dynamic Randomisation: Pod names, IPs, PIDs, nodes re-randomised every episode.

Noise-Buried Signals: Critical anomaly hidden among 14 realistic HTTP log lines.

Multi-Step Enforcement: Insane requires 3-service trace. Apocalypse requires 5 steps.

Dedup Penalty: -5% health for repeating same command and target.

Prometheus Metrics: /metrics endpoint exposes real operational telemetry.

Shaped Rewards: Each investigation step rewarded to encourage reasoning.

6 Difficulty Tiers: Easy, Medium, Hard, Extreme, Insane, Apocalypse.

## Difficulty Tiers

easy: Pod thread pool exhaustion. Fix: restart_pod. Steps: 1-2.

medium: Bad DB deployment broke credentials. Fix: rollback_deploy database. Steps: 2.

hard: Layer 7 DDoS on ingress. Find IP in logs. Fix: block_ip. Steps: 2.

extreme: Java memory leak. Find PID via run_top. Fix: kill_process. Steps: 2.

insane: Cascading frontend to payment to redis OOM. Fix: flush_cache redis-cache-cluster. Steps: 4.

apocalypse: Multi-region DB split-brain plus DDoS plus OOM plus Cache. Fix: 5 coordinated steps. Steps: 5-6.

## Agent Architecture

Planning Phase: explicit 1-sentence plan before each action.

ReAct Framework: thought plus confidence plus command plus target JSON.

Episodic Memory: remembers solutions from all previous tasks.

Confidence Scoring: below 0.75 means investigate more first.

Self-Correction: corrective prompt injected on invalid JSON.

Fault Tolerance: 3-attempt retry with 2s exponential backoff.

Context Window: last 2000 chars of terminal for full log parsing.

Model: Qwen/Qwen2.5-72B-Instruct at temperature 0.0 deterministic.

## API

POST /reset?task=easy - Start new episode.

POST /step - Execute agent action.

GET /state - Current state JSON.

GET /tasks - List all 6 tasks.

GET /metrics - Prometheus format metrics.

GET /grade/taskname - Task score.

GET /analytics - Full agent info.

## Commands

get_logs: exact service name.

get_metrics: exact service name.

run_top: exact node name.

restart_pod: exact pod name from alert.

rollback_deploy: always database.

block_ip: exact IP from logs.

kill_process: exact PID from run_top.

flush_cache: always redis-cache-cluster.

## License

MIT License 2026 Rishwanth Raju
