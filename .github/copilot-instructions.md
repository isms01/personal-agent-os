# Instructions for GitHub Copilot

## Language/Runtime
* Use Python 3.12 features and type hints.
* Prefer standard library first; add dependencies only when necessary.
* Follow PEP 8 conventions.

## Coding style
* Keep functions small and single-purpose (max ~20 lines).
* Prefer explicit names over abbreviations.
* Use early returns to reduce nesting.
* Document complex logic with inline comments.

## Error handling & logging
* Raise domain-specific exceptions (avoid bare `Exception`).
* Log actionable context (ids, counts) but **never secrets or PII**.
* Use structured logging where possible.

## Testing
* Write pytest tests for new logic.
* Cover edge cases: empty input, None, invalid states, boundary values.
* Prefer deterministic tests (mock time/random, avoid sleeps).
* Use fixtures for reusable test data.

## Project workflow
* Assume CI runs: format (ruff/black), lint, typecheck (mypy), tests.
* If changes break interfaces, update all call sites in the same PR.
* Check `pyproject.toml` for project-specific tool configs.

## Output requirements (for Copilot Chat)
* When suggesting code: provide **brief plan → code → tests**.
* If information is missing: **ask before assuming**.
* Respond in **Japanese** unless code/technical terms require English.

## Generation constraints
* **Max 300 lines per suggestion** (small PRs are easier to review).
* Split large features into multiple steps if needed.
* Prioritize readability over cleverness.