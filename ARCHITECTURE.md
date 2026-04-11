# 🏛️ KubeSRE v4.0: System Architecture & Theoretical Framework

## 1. Temporal Degradation Engine (TDE)
Health starts at 100. Every wrong fix costs -15%. Every duplicate action costs -5%.
Agent has max 12 steps. Forces zero-shot precision reasoning.

$$H_t = H_{t-1} - 15.0 \text{ (wrong fix)}$$
$$H_t = H_{t-1} - 5.0 \text{ (duplicate action)}$$

## 2. Stochastic State Generation (Anti-Cheat)
Every POST /reset randomises:
- Pod names: auth-service-{1000-9999}
- Attacker IPs: {10-255}.{0-255}.{0-255}.{1-254}
- Worker nodes: worker-node-{1-20}
- Memory leak PIDs: {10000-99999}
- DB versions: v{2-5}.{0-9}.{0-9}

Forces agents to actually read logs — memorisation is impossible.

## 3. Needle in a Haystack Log Synthesizer
get_logs generates 14 realistic HTTP access log lines.
Critical anomaly injected at random index i in [2,12].
Agent must filter semantic noise and extract exact target values.

## 4. Multi-Step Reasoning Enforcement

### Insane Task (3-service cascade):
