---
title: KubeSRE Incident Env
emoji: 🚨
colorFrom: red
colorTo: orange
sdk: docker
pinned: false
---

# KubeSRE: Autonomous SRE Environment

A high-fidelity OpenEnv-compatible SRE simulation for evaluating autonomous agents under realistic production failure conditions.

## API

### Reset
`POST /reset?task=easy` — tasks: easy, medium, hard, insane

### Step
`POST /step` — body: `{"command": "...", "target": "..."}`

### Health
`GET /health`