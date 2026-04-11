# Contributing to KubeSRE

Thank you for your interest in contributing to KubeSRE OpenEnv v4.0.

## How to Add a New Task

1. Add dynamic variables to ServerState in server/app.py
2. Add task config to get_tasks() function
3. Add get_logs anomaly handling for your service
4. Add solution command handling in the step() route
5. Add grade score to SCORES dict
6. Add task to openenv.yaml
7. Add task to inference.py task list

## Rules for New Tasks

- Alert must NOT reveal the exact fix command
- Target must be randomised every reset (no memorisation)
- Anomaly must be buried in 14+ noise log lines
- Multi-step tasks must require 2+ investigation steps
- Wrong fix must cost -15% health

## Chaos Testing

Add malicious payloads to chaos_test.py CHAOS_ACTIONS array.
Server must handle all inputs gracefully (HTTP 200 or 422).
Zero server crashes is the target.

## Reward Design Rules

- Investigation steps: 0.15-0.45 reward
- Correct fix without investigation: 0.20-0.25
- Correct fix with full investigation: 0.95
- Duplicate action: 0.00 with -5% health penalty
- Wrong fix: 0.05 with -15% health penalty
