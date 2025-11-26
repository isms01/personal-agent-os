# ai-schedule-assistant

> "思想は具現化されて初めて意味を持つ" - [FOUNDATION.md](doc/FOUNDATION.md)

AI scheduling assistant with smart calendar management.

## Vision

Reduce human "task work" and enable focus on true value creation through AI agent automation.

See [FOUNDATION.md](doc/FOUNDATION.md) for design philosophy.

## Development Status

**Current:** Sprint 1 - Basic Chat Assistant  
**Progress:** [TODO.md](TODO.md) | [progress-log.md](progress-log.md)

## Core Values

1. **Pragmatic First** - 実用性優先
2. **Learn By Building** - 手を動かして理解
3. **Explainability** - 説明可能性

## Tech Stack

- Python 3.12
- Claude API (Anthropic)
- Poetry

## Setup
```bash
# Install dependencies
poetry install

# Configure API key
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# Run (coming soon)
poetry run python app/main.py
```

## Structure
```
ai-schedule-assistant/
├── app/
│   ├── agents/    # AI agent implementations
│   └── tools/     # Tool implementations
├── tests/         # Unit tests
├── doc/           # Documentation
│   └── FOUNDATION.md
├── TODO.md
└── progress-log.md
```

## Timeline

12 weeks, 6 sprints for career portfolio

## License

TBD
EOF