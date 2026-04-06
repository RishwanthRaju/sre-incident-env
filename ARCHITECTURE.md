# 🏛️ KubeSRE: System Architecture & Theoretical Framework

This document outlines the core architectural decisions, mathematical constraints, and AI behavioral theories that drive the **KubeSRE OpenEnv Benchmark**.

---

## 1. The Temporal Degradation Engine (TDE)
Current LLM benchmarks (e.g., WebArena, SWE-bench) typically offer agents infinite or highly generous step limits, allowing models to randomly guess actions until successful. KubeSRE introduces strict **Temporal Degradation**.

### Mathematical Constraint:
Let $H_t$ represent the Cluster Health at step $t$, where $H_0 = 100.0$.
For any action $A_t$ that does not resolve the root cause:
$$H_t = H_{t-1} - 15.0$$

**Theoretical Implication:** 
This engine forces the LLM to abandon "brute-force" or hallucinatory strategies. An agent only has a maximum of **6 steps** to diagnose and mitigate an incident before $H_t \le 0$ (Fatal Crash). This heavily selects for models capable of high-precision, zero-shot deductive reasoning.

---

## 2. Stochastic State Generation (Anti-Cheat)
A primary flaw in static environments is model memorization (overfitting). If an environment always triggers a DDoS attack from `10.0.0.99`, a model will memorize the target rather than parsing the logs.

### Procedural Generation Matrix:
Upon every `POST /reset`, the KubeSRE state engine seeds random variables:
*   **Attack Vectors:** Layer 7 DDoS IPs ($IP \in [10.255].[0.255].[0.255].[1.254]$).
*   **Process IDs (PIDs):** Memory leaks are bound to dynamic integer strings $PID \in [10000, 99999]$.
*   **Node Topology:** Failing pods and worker nodes are randomly assigned IDs.

**Theoretical Implication:**
The agent is mathematically forced to execute reconnaissance tools (`get_logs`, `run_top`), parse the unstructured simulated stdout, and dynamically extract the unique variables required for the mitigation tool (`kill_process`, `block_ip`).

---

## 3. The "Needle in a Haystack" (NIAH) Log Synthesizer
In the real world, errors do not exist in isolation; they are buried within massive streams of routine telemetry. 

### The Noise Algorithm:
When an agent requests logs via `get_logs('target')`:
1.  The environment generates $N=15$ lines of routine HTTP GET requests, health checks, and standard background daemon processes.
2.  The critical anomaly (the "Needle") is randomly inserted at index $i \in [2, 12]$.

**Theoretical Implication:**
This tests the LLM's **Context Window Attention Mechanism**. The model must filter out semantic noise, identify the critical exception trace, and retain that context for the subsequent action.

---

## 4. Forced Chain-of-Thought (ReAct) Topology
KubeSRE is designed to evaluate agents using the **ReAct (Reasoning + Acting)** framework.

### Prompt Engineering Protocol:
The baseline agent is instructed via the System Prompt to output a strictly typed JSON payload containing a `thought` key prior to the `command` key.

```json
{
  "thought": "The frontend is throwing a 504 Gateway Timeout. This indicates it cannot reach the downstream service. I must execute get_logs on the payment-gateway.",
  "command": "get_logs",
  "target": "payment-gateway"
}
