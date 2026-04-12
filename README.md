---
title: KubeSRE Incident Env
emoji: 🚨
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
---

# KubeSRE Incident Response Environment

KubeSRE is a production-inspired OpenEnv environment for evaluating whether AI agents can diagnose and resolve realistic Kubernetes and infrastructure incidents under temporal pressure.

Built by Rishwanth Raju for the Meta PyTorch OpenEnv Hackathon 2026.

## Why this environment matters

Most tool-use benchmarks test shallow API calling. KubeSRE tests operational reasoning.

Agents must:
- inspect logs, metrics, and system state,
- ignore noisy but irrelevant observations,
- identify exact dynamic targets such as pod names, PIDs, IPs, and nodes,
- choose the correct remediation action,
- avoid duplicate or premature fixes,
- solve multi-hop cascading failures across services.

This makes KubeSRE useful for both training and evaluating agent reliability in high-pressure DevOps and SRE workflows.

## Core features

- 6 difficulty tiers: easy, medium, hard, extreme, insane, apocalypse
- Dynamic randomization of pod names, IPs, PIDs, nodes, and log positions
- Multi-step investigation before remediation
- Reward shaping that discourages blind action-taking
- Realistic noisy log streams with hidden anomalies
- Metrics and analytics endpoints for observability
- Clear task-specific grading endpoints

## Task ladder

### Easy — Pod Latency Spike
Investigate an overloaded auth pod and restart the correct target.

### Medium — Database Credential Failure
Trace a failed deployment and rollback the affected service.

### Hard — Layer 7 DDoS Attack
Find the attacker IP buried in noisy ingress logs and block it.

### Extreme — Java Memory Leak
Use node-level process inspection to identify and kill the leaking PID.

### Insane — Cascading Microservice Failure
Follow a service chain from frontend to payment to Redis, then flush the cache.

### Apocalypse — Multi-Region Catastrophe
Handle a compound failure involving split-brain symptoms, resource overload, attack traffic, and cache collapse across multiple systems.

## Why it is hard

KubeSRE is designed so agents cannot simply memorize answers.

- Targets are randomized at reset time.
- Relevant evidence is mixed with realistic noise.
- Correct remediation often requires investigation first.
- Duplicate or careless actions reduce health and reward.
- Higher tiers require cross-service reasoning rather than single-step fixes.

## API

### Reset environment
`POST /reset?task=easy`

### Execute one action
`POST /step`

### Inspect current state
`GET /state`

### Prometheus-style metrics
`GET /metrics`

### Episode analytics
`GET /analytics`

## Tasks

- easy
- medium
- hard
- extreme
- insane
- apocalypse

## Evaluation philosophy

This environment is judged on real-world utility, task and grader quality, environment design, code/spec compliance, and creativity. KubeSRE is intentionally built to score strongly on all five by combining realistic operational tasks, dynamic state generation, measurable outcomes, and meaningful difficulty progression.

## Repository structure

- `server/app.py` — main environment server
- `server/inference.py` — agent inference entrypoint
- `openenv.yaml` — OpenEnv metadata and task definitions
- `ARCHITECTURE.md` — environment design notes
- `INCIDENTS.md` — task-by-task incident breakdown
- `EVALUATION.md` — benchmark results and analysis

## License

MIT 2026 Rishwanth Raju
