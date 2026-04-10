---
title: 🛡️ KubeSRE: Autonomous SRE Environment
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: fastapi
sdk_version: 0.104.1
python_version: 3.11
app_file: app.py
pinned: false
---

# 🛡️ KubeSRE: Autonomous SRE Environment

A **high-fidelity OpenEnv-compatible SRE simulation** for evaluating autonomous agents under **realistic production failure conditions**.

---

# 🚀 What Makes This Different

Most environments allow brute-force guessing.

**KubeSRE does NOT.**

It enforces:
- ⛔ Strict step limits  
- ⛔ Health degradation (-15% per mistake)  
- ⛔ Noisy logs (signal buried in noise)  
- ⛔ Dynamic targets (no memorization)

➡️ Agents must **reason correctly — or fail**

---

# 🧠 Environment Design

### 🔻 Temporal Degradation
- Each incorrect action reduces system health
- Failure at 0%
- Forces **efficient decision-making**

### 🎯 Dynamic Incidents
- Randomized pods, IPs, PIDs
- Prevents hardcoded solutions

### 🔍 Noisy Logs
- Realistic production noise
- Critical signals hidden

---

# ⚙️ API

### Reset