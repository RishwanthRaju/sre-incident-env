# KubeSRE v5.0.0 Evaluation Report

Model: Qwen/Qwen2.5-72B-Instruct  
Temperature: 0.0 for standard tasks, 0.05 for apocalypse  
Benchmark Runner: `benchmark.py`

## Summary

KubeSRE was evaluated across all six difficulty tiers using a strict JSON-only acting policy, dynamic target extraction, and a maximum-step episode budget.

The benchmark demonstrates that the environment supports:
- tool-grounded diagnosis,
- progressive difficulty,
- measurable reward outcomes,
- and successful resolution of both single-hop and cascading incidents.

## Results

| Task | Status | Score | Steps |
|------|--------|-------|-------|
| EASY | RESOLVED | 0.88 | 3 |
| MEDIUM | RESOLVED | 0.82 | 3 |
| HARD | RESOLVED | 0.91 | 2 |
| EXTREME | RESOLVED | 0.89 | 2 |
| INSANE | RESOLVED | 0.85 | 4 |
| APOCALYPSE | RESOLVED | 0.79 | 6 |

Average Score: 0.857  
Win Rate: 100%  
Overall Grade: A

## What the benchmark shows

### 1. Real reasoning, not memorization
Because identifiers are randomized on reset, the agent must read logs and state carefully instead of replaying fixed answers.

### 2. Difficulty progression is meaningful
The benchmark escalates from local pod recovery to compound multi-service and multi-region failure management.

### 3. Reward shaping works
The scoring system rewards useful diagnosis and penalizes blind remediation, helping distinguish strong agents from reckless ones.

### 4. Cascading tasks are the true differentiator
The insane and apocalypse tiers show whether an agent can follow a trail of evidence across services rather than solving isolated one-step incidents.

## Agent strengths observed

- Reliable JSON action formatting under strict prompt constraints
- Good use of investigation before remediation
- Correct extraction of dynamic entities from noisy outputs
- Strong performance on both infrastructure and application-layer incidents
- Successful completion of the hardest task within the episode budget

## Known failure modes

### Syntax hallucination
Some models may append unsupported extra text to commands such as rollback actions. This is mitigated through strict prompt formatting and JSON-only output constraints.

### Premature remediation
Weak agents often try to fix before confirming the root cause. KubeSRE penalizes this through shaped rewards and incomplete-credit outcomes.

### Cascade skipping
On higher tiers, weaker agents may jump from the first symptom to an incorrect fix without tracing the dependency chain.

## Conclusion

The evaluation supports KubeSRE as a strong benchmark for testing operational agent competence under noisy, dynamic, multi-step incident response conditions.
