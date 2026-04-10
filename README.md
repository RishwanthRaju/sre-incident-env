# 🛡️ KubeSRE: Autonomous SRE Agent

**100% Win Rate** across 5 incident tiers. Fixed rollback syntax hallucination (80% → 100%).

## 🏆 Benchmark Results (15/15 runs)
| Task | Success | Steps | Score |
|------|---------|-------|-------|
| EASY | 100% | 3.0 | 0.950 |
| MEDIUM | 100% | 1.0 | 0.950 |
| HARD | 100% | 2.0 | 0.950 |
| EXTREME | 100% | 2.0 | 0.950 |
| INSANE | 100% | 3.0 | 0.950 |

**Overall: 100% Win Rate | 0.950 Avg Score**

## 🚀 Live Demo
```bash
uvicorn app:app --port 7860
python inference.py  # Watch agent solve live
```

## 💡 Innovations
- Temporal health degradation (-15% per wrong step)
- Noisy production logs 
- Episodic memory (remembers solutions)
- Confidence gating (>85% before action)
- Dynamic targets (random pod/IP/PID)

## 📈 Proof
[![Benchmark Proof](./KUBESRE_PROOF_*.json)](./KUBESRE_PROOF_*.json)

## 🛠️ Setup
```bash
pip install -r requirements.txt
uvicorn app:app --port 7860
python inference.py
```