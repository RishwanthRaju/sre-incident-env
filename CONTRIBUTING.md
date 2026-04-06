# 🤝 Contributing to KubeSRE

Thank you for your interest in contributing to the **KubeSRE Autonomous Agent Benchmark**! 

As frontier models (like GPT-4, Claude 3, and Qwen) become more advanced, we need to continuously scale the difficulty of our simulated SRE environments. We welcome contributions from AI researchers, DevOps engineers, and the open-source community.

## 🚀 How to Add a New Difficulty Tier (Task)

If you want to add a "Level 6" or higher task to the environment, please follow the strict OpenEnv specifications.

1. **Define the Alert:** The alert must be a red herring or require multi-hop debugging. Do not make the root cause obvious.
2. **Update the State Matrix:** In `server/app.py`, locate the `ServerState` class. Add any new dynamic variables (e.g., randomized VPC networks, AWS IAM roles, or database port numbers) to ensure the new task remains Anti-Cheat.
3. **Generate Log Noise:** Use the `generate_log_noise()` function to bury your anomaly trace inside at least 15-20 lines of standard HTTP or sys-daemon traffic.
4. **Verify the RL Grader:** Ensure your new task can be mathematically solved. The `benchmark.py` suite must be able to calculate the `max_possible_reward` based on the optimal path length.

## 🐛 Bug Reports & Chaos Testing
If you find a prompt injection or payload that crashes the FastAPI server, please add the payload to the `CHAOS_ACTIONS` array inside `chaos_test.py` and submit a Pull Request. We strive for a 0% server crash rate under all hallucinated LLM conditions.
