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
Current LLM agent benchmarks evaluate static, turn-based tasks (e.g., web scraping, email sorting) with infinite time horizons. In real-world Site Reliability Engineering (SRE), **time is the enemy, logs are noisy, and targets are never hardcoded.** 

**KubeSRE** introduces a highly volatile, non-deterministic environment designed specifically to stress-test frontier ReAct (Reasoning + Acting) models under simulated production outages.

## 🚀 Core Architectural Innovations

### 1. Temporal Degradation Engine (Anti-Hallucination)
KubeSRE penalizes inefficient reasoning. Every step the agent takes without resolving the root cause degrades cluster health by **15%**. If the agent hallucinates tools, spams incorrect commands, or gets stuck in a loop, the simulated environment triggers a `FATAL SYSTEM CRASH`. 

### 2. Stochastic Generation (Anti-Memorization)
To prevent agents from overfitting or memorizing static solutions, KubeSRE utilizes dynamic state generation on every `reset()`.
* **Randomized Attack Vectors:** Layer 7 DDoS IPs are procedurally generated (e.g., `64.74.35.18`).
* **Dynamic Linux Processes:** OOM (Out of Memory) alerts require agents to parse a randomized Linux process tree and extract the exact dynamic PID of the memory leak. 

### 3. Needle in a Haystack (Log Noise)
Real production environments do not return a single line of text. When an agent executes `get_logs` or `run_top`, KubeSRE generates blocks of realistic, dynamic HTTP traffic and background process noise. The agent must utilize its reasoning to locate the true anomaly hidden deep within the simulated logs.

### 4. Cascading Microservice Failures (Breadcrumb Tracing)
Advanced tasks feature "Red Herring" alerts. An agent might receive a 500 Error on the `frontend-service`. It must parse the logs, trace the timeout to the `payment-gateway`, read those logs, trace the failure to `redis-cache-cluster`, and execute a `flush_cache` command to save the system. This evaluates true multi-hop autonomous debugging.

## 🗺️ System Architecture: The "Insane" Microservice Cascade
Here is the exact path the ReAct agent must navigate to prevent a system crash:

```mermaid
graph TD
    A[🚨 Alert: Frontend 500 Error] -->|Action: get_logs| B(Frontend Service)
    B -->|Log: Timeout reaching Gateway| C(Payment Gateway)
    C -->|Action: get_logs| C
    C -->|Log: Connection Refused to Cache| D(Redis Cluster)
    D -->|Action: get_logs| D
    D -->|Log: OOM Fatal Error| E{Action: flush_cache}
    E -->|Reward: +1.0| F((✅ System Saved))
    
    style A fill:#ffe6e6,stroke:#ff0000,stroke-width:2px
    style E fill:#e6ffe6,stroke:#00cc00,stroke-width:2px
    style F fill:#ccffcc,stroke:#009900,stroke-width:2px
