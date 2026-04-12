# KubeSRE v5.0.0 Architecture

## Overview

KubeSRE is a production-grade SRE incident response environment built for OpenEnv. It evaluates whether an agent can investigate, reason, and remediate realistic infrastructure failures across Kubernetes-style services under strict step and health constraints.

## Design goals

The environment was designed around five principles:

1. Real-world operational utility
2. Clear and fair grading
3. Dynamic anti-memorization state generation
4. Multi-step reasoning pressure
5. Clean episode boundaries with measurable outcomes

## Environment loop

Each episode begins with a task-specific reset. The agent receives an observation containing:
- active alerts,
- current system health,
- terminal output,
- task context.

The agent then issues one action at a time through the environment API. Each action changes state, generates new observations, and contributes to cumulative reward.

## State model

KubeSRE tracks:
- system health,
- current step count,
- active task,
- dynamic service identifiers,
- terminal/log output,
- reward trajectory,
- completion status.

Episodes terminate when:
- the incident is successfully resolved,
- health reaches zero,
- the maximum step limit is hit,
- or the task marks itself done after a terminal action.

## Temporal degradation engine

Health begins at 100 and degrades when the agent makes poor choices.

Typical penalties include:
- wrong remediation,
- duplicate actions,
- wasted steps,
- premature fixes without investigation.

This forces the agent to balance speed and caution like a real SRE workflow.

## Dynamic randomization

To prevent answer memorization, the environment randomizes critical identifiers on reset:
- pod names,
- node names,
- process IDs,
- attacker IPs,
- anomaly positions in log streams.

This ensures that success depends on interpreting evidence, not recalling fixed strings.

## Observation design

The observation space is intentionally compact but meaningful. Agents do not get direct ground-truth answers. Instead, they must extract them from:
- noisy terminal output,
- service logs,
- system metrics,
- process inspection results.

Noise filtering is part of the challenge.

## Action space

The environment exposes a restricted but realistic tool set:
- `get_metrics`
- `get_logs`
- `run_top`
- `restart_pod`
- `rollback_deploy`
- `block_ip`
- `kill_process`
- `flush_cache`

This action space is narrow enough to grade reliably and rich enough to support multi-step diagnosis.

## Difficulty progression

### Easy
Single-service restart after log confirmation.

### Medium
Deployment rollback after identifying bad credentials.

### Hard
Find and block an attacker IP hidden in noisy logs.

### Extreme
Inspect node-level processes and kill the leaking PID.

### Insane
Trace a cascading dependency failure across three services.

### Apocalypse
Handle a compound, multi-system incident involving distributed failure signals and coordinated remediation.

The ladder is designed so each tier adds either ambiguity, indirection, or coordination burden.

## Reward shaping

KubeSRE uses shaped rewards so the benchmark can distinguish intelligent investigation from lucky guessing.

Examples:
- small reward for useful investigation,
- stronger reward for locating critical anomalies,
- highest reward for correct remediation after proper diagnosis,
- low or zero reward for duplicate, blind, or incorrect actions.

This encourages interpretable stepwise reasoning instead of brute-force tool spamming.

## Grading model

Each task has a dedicated grader endpoint declared in `openenv.yaml`. Graders evaluate whether the agent solved the right problem using the right action sequence under the episode constraints.

This keeps scoring transparent and task-specific.

## Observability

KubeSRE includes observability endpoints such as:
- `GET /state`
- `GET /metrics`
- `GET /analytics`

Metrics include health, step progression, episode resolution, command counts, reward averages, and elapsed time. This makes runs easy to inspect and compare.

## Why KubeSRE is hard to game

KubeSRE is intentionally robust against shallow benchmark exploitation:
- dynamic targets break memorization,
- noisy logs punish superficial pattern matching,
- cascading tasks require following evidence across services,
- partial-credit structure penalizes premature fixes,
- strict task-specific tools reduce ambiguity while preserving challenge.

## OpenEnv compliance

KubeSRE is packaged as an OpenEnv HTTP environment with:
- `openenv.yaml`,
- Docker-based deployment,
- documented endpoints,
- clear task metadata,
- reproducible grading hooks.

## Summary

KubeSRE combines realistic SRE workflows, dynamic environment state, fair task grading, and meaningful multi-step reasoning pressure into a benchmark that is both practically useful and difficult for weak agents to fake.
