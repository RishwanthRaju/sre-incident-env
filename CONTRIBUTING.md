# Contributing to KubeSRE

Thank you for your interest in contributing to KubeSRE.

KubeSRE is a production-inspired OpenEnv environment for evaluating agent performance on realistic SRE incident response tasks. Contributions should preserve the benchmark’s difficulty, fairness, and reproducibility.

## Contribution principles

Please keep these goals in mind when making changes:

- Maintain realistic incident-response workflows.
- Preserve dynamic randomization of targets such as pod names, PIDs, IPs, and nodes.
- Keep task grading clear, deterministic, and reproducible.
- Avoid changes that make tasks trivial, scripted, or easily memorizable.
- Keep documentation and versioning consistent across the repository.

## How to add a new task

1. Add any required dynamic variables to the environment state in `server/app.py`.
2. Add the task configuration to the task registry or `get_tasks()` logic.
3. Add the relevant anomaly and noisy observations to the log-generation flow.
4. Add task-specific solution handling in the environment step logic.
5. Add or update the reward and scoring configuration.
6. Add the task metadata and grader endpoint to `openenv.yaml`.
7. Add the task to any inference, routing, or benchmark task lists.
8. Test the task end-to-end before committing.

## Task design rules

All new tasks should follow these design rules:

- Alerts should not reveal the remediation command directly.
- Critical targets must be randomized on every reset.
- Relevant evidence should be mixed with realistic noise.
- Multi-step tasks should require investigation before remediation.
- Higher-difficulty tasks should involve ambiguity, indirection, or service-to-service dependency tracing.
- The task must be solvable through observation and reasoning, not by guessing.

## Reward design rules

Reward shaping should distinguish careful diagnosis from reckless action-taking.

Recommended pattern:

- Investigation steps: small positive reward when they uncover useful evidence
- Correct remediation without sufficient investigation: partial credit only
- Correct remediation after proper investigation: high reward
- Duplicate actions: zero or minimal reward, plus state penalty if appropriate
- Incorrect remediation: low reward and meaningful health penalty

Keep reward logic consistent with the rest of the benchmark.

## Grading rules

When adding or editing tasks:

- Ensure the grader checks the correct resolution condition.
- Keep grader behavior deterministic and easy to audit.
- Avoid vague success criteria.
- Make sure the grader reflects the intended task path and acceptable solution space.

## Chaos and robustness testing

KubeSRE should remain robust under malformed or adversarial inputs.

When changing the environment:

- Add adversarial or malformed actions to `chaos_test.py` when relevant.
- Verify the server handles bad inputs gracefully.
- Prevent crashes, invalid state transitions, and silent failures.
- Treat zero server crashes as a baseline quality target.

## Documentation updates

If you add or change a task, also update the relevant documentation:

- `README.md`
- `ARCHITECTURE.md`
- `INCIDENTS.md`
- `EVALUATION.md` if benchmark behavior changes
- `openenv.yaml` if task metadata changes

## Pull requests

A good pull request should include:

- a short summary of the change,
- affected files,
- whether task logic changed,
- whether grader logic changed,
- and any benchmark impact.

Small, focused pull requests are preferred over large mixed changes.

## Code style

Prefer explicit, readable code over clever abstractions.

Keep logic:
- modular,
- easy to inspect,
- and aligned with benchmark reproducibility.

## License

By contributing to this repository, you agree that your contributions will be released under the repository license.
