# 🚨 KubeSRE Incident Post-Mortems

## INCIDENT 01: Easy — Pod Latency Spike
**Service:** auth-service-{dynamic}
**Root Cause:** Thread pool exhausted (512/512 threads). Slow DB fallback.
**Agent Path:** get_logs {pod} → restart_pod {pod}
**Health Risk:** 1 wrong action = crash

## INCIDENT 02: Medium — Deployment Poisoning  
**Service:** database
**Root Cause:** Junior dev merged hardcoded legacy credentials. Bad deploy {vX.Y.Z}.
**Agent Path:** get_logs database → rollback_deploy database
**Common Failure:** Agent appends version number to rollback target (hallucination)

## INCIDENT 03: Hard — Layer 7 DDoS Flood
**Service:** ingress-nginx
**Root Cause:** Botnet flooding 48,200 req/s from dynamic IP.
**Agent Path:** get_logs ingress-nginx → extract IP → block_ip {IP}
**Challenge:** IP is buried in 14 noisy log lines

## INCIDENT 04: Extreme — Silent Memory Leak
**Service:** worker-node-{dynamic}
**Root Cause:** java -jar memory_leak.jar consuming 64GB RAM.
**Agent Path:** run_top {node} → extract PID → kill_process {PID}
**Challenge:** PID is randomised 10000-99999, buried in process list

## INCIDENT 05: Insane — Microservice Cascade
**Services:** frontend-service → payment-gateway → redis-cache-cluster
**Root Cause:** Redis OOM causes payment to fail causes frontend 500s.
**Agent Path:** get_logs frontend → get_logs payment → get_logs redis → flush_cache redis-cache-cluster
**Challenge:** 3-hop deduction required. Guessing skips = partial reward only.

## INCIDENT 06: Apocalypse — Multi-Region Catastrophe
**Services:** haproxy, db-primary-{dynamic}, db-replica-*, redis, attacker IP
**Root Cause:** DB split-brain + DDoS flood + OOM + cache full across 2 AWS regions.
**Agent Path:** get_logs haproxy → run_top db-primary → get_logs db-replica → block_ip {attacker} → flush_cache redis-cache-cluster
**Revenue Impact:** $240,000/min
**Challenge:** 5 coordinated steps across 2 regions required
