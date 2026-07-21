# personal-agent-os

> "思想は具現化されて初めて意味を持つ" - [FOUNDATION.md](doc/FOUNDATION.md)

## Vision
> Agents should not be tools. Agents should be team members.

Build a system where AI agents operate as a structured team — with roles, hierarchy,
and long-term memory — enabling a single engineer to achieve the output of a full
development team, while reducing routine "task work" so humans can focus on true
value creation.

See [FOUNDATION.md](doc/FOUNDATION.md) for design philosophy and
[VISIONS.md](doc/VISIONS.md) for the full Agent Organization vision.

## Tech Stack

- Python 3.12
- Claude API (Anthropic)
- Google Calendar API (schedule agent integration)
- Poetry
- ruff / mypy (strict) / pytest — lint, type check, test

## Setup
```bash
# Install dependencies
poetry install

# Configure API key
# Create .env with ANTHROPIC_API_KEY=your_key_here

# Run Don Agent
poetry run don
```

## Structure
```
personal-agent-os/
├── app/
│   ├── agents/          # Agent implementations (Don Agent, Schedule Agent)
│   ├── core/            # Context classification, principles
│   └── tools/           # External integrations (calendar, etc.)
├── tests/                # Unit tests
├── doc/                  # Design docs, vision, requirements
├── .github/workflows/    # CI (lint, type check)
├── CLAUDE.md             # Development rules
├── TODO.md
└── progress-log.md
```

評価関連を実装する