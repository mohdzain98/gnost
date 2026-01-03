# Contributing to GNOST

Thanks for your interest in contributing! This guide outlines a simple workflow and expectations.

## Quick Start
1. Fork the repo and create a feature branch.
2. Set up your environment.
3. Make focused changes with tests or examples when possible.
4. Open a PR with a clear description and context.

## What to Contribute
We welcome contributions in the following areas:
- Bug fixes and stability improvements
- Onboarding insights and analysis logic
- Documentation improvements (ReadTheDocs, examples)
- CLI usability enhancements
- Language adapters and scanners

If you’re unsure where to start, open a discussion or issue first.

## Setup
```bash
git clone https://github.com/mohdzain98/gnost.git
cd gnost
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Development Guidelines
- Keep changes scoped and well-described.
- Maintain a professional, open-source friendly tone in code and docs.
- Prefer small, reviewable commits.
- Avoid formatting churn unrelated to your change.

## Architecture Notes
GNOST follows a clear separation of concerns:
- Scanners analyze code
- Core logic builds flow and insights
- Reporters render output (terminal, markdown, diagrams)

`Please avoid mixing analysis logic into reporters or CLI commands.`

## Testing
If you add behavior, add or update tests when possible.

```bash
pytest
```

## Documentation
- User-facing changes should update docs or README when needed.
- Longer docs belong in ReadTheDocs instead of README.

## Submitting a PR
- Describe what changed and why.
- Link related issues or discussions if applicable.
- Note any follow-up work or limitations.

## Code of Conduct
Be respectful and constructive in all interactions.
