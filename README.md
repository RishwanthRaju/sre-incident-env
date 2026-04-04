---
title: SRE Incident Env
emoji: 🚨
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
tags:
  - openenv
---

# 🚨 KubeSRE-OpenEnv: The Frontier Benchmark for Autonomous SRE Agents

## 🏆 The Problem with Current AI Benchmarks
Current LLM agent benchmarks evaluate static, turn-based tasks (e.g., web scraping, email sorting) with infinite time horizons. In real-world Site Reliability Engineering (SRE), **time is the enemy, and targets are not hardcoded.** 

**KubeSRE** introduces a highly volatile, non-deterministic environment designed specifically to stress-test frontier ReAct (Reasoning + Acting) models under simulated production outages.

## 🚀 Core Architectural Innovations

### 1. Temporal Degradation Engine (Anti-Hallucination)
KubeSRE penalizes inefficient reasoning. Every step the agent takes without resolving the root cause degrades cluster health by **15%**. If the agent hallucinates tools, spams incorrect commands, or gets stuck in a loop, the simulated environment triggers a `FATAL SYSTEM CRASH`. 

### 2. Stochastic Generation (Anti-Memorization)
To prevent agents from overfitting or memorizing static solutions, KubeSRE utilizes dynamic state generation on every `reset()`.
* **Randomized Attack Vectors:** Layer 7 DDoS IPs are procedurally generated (e.g., `64.74.35.18`).
* **Dynamic Linux Processes:** OOM (Out of Memory) alerts require agents to execute `run_top`, parse a randomized Linux process tree, and extract the exact PID of the memory leak. 

### 3. Cascading Microservice Failures (Breadcrumb Tracing)
Advanced tasks feature "Red Herring" alerts. An agent might receive a 500 Error on the `frontend-service`. It must parse the logs, trace the timeout to the `payment-gateway`, read those logs, trace the failure to `redis-cache-cluster`, and execute a `flush_cache` command to save the system. This evaluates true multi-hop autonomous debugging.

## 🛠️ The 5-Tier Evaluation Matrix
Agents are evaluated across a difficulty gradient utilizing 8 distinct terminal commands.

* **Level 1 (Easy):** Resolve a Prometheus latency alert via pod restart.
* **Level 2 (Medium):** Identify bad database credentials via Datadog logs and initiate a deployment rollback.
* **Level 3 (Hard):** Investigate a 99% CPU ingress spike, dynamically extract the attacking IP from Nginx logs, and execute an IP block.
* **Level 4 (Extreme):** Respond to an AWS CloudWatch OOM alert, run a terminal top command, identify the dynamic PID of a Java memory leak, and execute a surgical process kill.
* **Level 5 (Insane):** Navigate a 3-hop microservice failure cascade (Frontend → Gateway → Cache) to identify the true root cause without crashing the system.

## 🎯 Continuous Reward Shaping Strategy
Compliant with strict OpenEnv RL specifications `[0.0 - 1.0]`:
* **+0.15 to +0.30**: Dense rewards for executing correct diagnostic commands (`get_logs`, `run_top`) on the correct, dynamically generated targets.
* **+1.0**: Sparse terminal reward for surgical root-cause mitigation.
* **-15.0% System Health**: Temporal penalty for every step taken.
* **-0.1**: Immediate deduction for destructive or syntactically invalid commands.

## 💻 Reproducibility & OpenEnv Spec Compliance
Built with FastAPI and Pydantic, KubeSRE is fully typed, containerized, and OpenEnv-spec compliant.

```bash
# 1. Build the Docker container
docker build -t sre-env .

# 2. Run the environment locally
docker run -p 7860:7860 sre-env

# 3. Run the baseline OpenEnv ReAct agent
python inference.py