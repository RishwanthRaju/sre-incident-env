---
title: KubeSRE - Autonomous SRE Agent
emoji: 🚨
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
tags:
  - openenv
  - ai-agent
  - sre
---

# 🚨 KubeSRE: Autonomous AI Site Reliability Engineer

## 🏆 Project Overview
This project deploys a frontier **Autonomous SRE Agent** designed to diagnose and mitigate critical, cascading server incidents in a highly volatile, non-deterministic Kubernetes environment. 

While traditional LLM benchmarks test static trivia, this agent is engineered to survive **Temporal Degradation**, where every inefficient step degrades cluster health by 15%, leading to a fatal system crash at 0%.

## 🧠 Core AI Agent Architecture (inference.py)

To achieve maximum performance across all 5 difficulty tiers (Easy to Insane), this agent utilizes a highly specialized **ReAct (Reasoning + Acting)** framework combined with deterministic prompt engineering.

### 1. The "Needle in a Haystack" (NIAH) Context Parser
Production logs are incredibly noisy. When the environment generates HTTP/sys-daemon noise, the true anomaly is buried. 
* **The Upgrade:** The agent's context memory window was expanded to ingest the last **1500 characters** of raw terminal output. This allows the LLM to successfully parse massive Linux process trees (via `run_top`) and extract dynamic, randomized PIDs and Layer 7 DDoS IP addresses without truncation.

### 2. Multi-Hop Deductive Playbook
The agent is equipped with a strict chain-of-thought playbook mapped to the environment's incident vectors:
* **Anti-Hallucination:** Strictly enforces `rollback_deploy` syntax without appending hallucinated version numbers.
* **Cascading Failures:** For the "Insane" tier (Checkout API 500 errors), the agent is programmed to trace downstream: `frontend-service` $\rightarrow$ `payment-gateway` $\rightarrow$ `redis-cache-cluster`, mitigating the root OOM exception.

### 3. Zero-Shot Self-Healing Loop
LLMs occasionally output malformed JSON. Instead of crashing the server, this agent includes an enterprise-grade fallback mechanism:
* If the generated JSON is invalid, or the environment returns a `422` or `[ERROR]`, the Python runtime catches the exception.
* It injects a strict corrective prompt (`"PREVIOUS FAILED: Your command caused an error."`) back into the context window for the next step, forcing the agent to self-correct its syntax dynamically.

## ⚙️ Environment Configuration

* **Model:** `Qwen/Qwen2.5-72B-Instruct`
* **Temperature:** `0.0` (Strictly deterministic execution for maximum reliability)
* **Tasks Executed:** All 5 (`easy`, `medium`, `hard`, `extreme`, `insane`)
* **Infrastructure:** Bypasses Docker Hub rate-limiting via Google Container Registry (`mirror.gcr.io`) fallback.

## 🛡️ License
MIT License. Copyright (c) 2026 Rishwanth Raju.
