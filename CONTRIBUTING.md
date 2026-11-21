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
You need Python 3.9 or newer, git and `make` (on Windows use Git Bash or WSL).

```bash
git clone https://github.com/<your-username>/gnost.git   # your fork
cd gnost
make setup      # once: creates .venv and installs the git pre-commit hook
make install    # installs GNOST (editable) and every development tool into .venv
make check      # lint, formatting and tests: the same as CI
```

`make setup` also installs a git hook, so from then on every `git commit` runs the style checks
(ruff, whitespace, YAML and so on) and fixes what it can. If a commit is stopped, look at what the
hook changed, `git add` it and commit again.

The Makefile finds `.venv` by itself, so you do not need to activate it. If you want to, run
`source .venv/bin/activate` (`.venv\Scripts\activate` on Windows).

### Useful commands
Run `make help` to see them all.

| Command | What it does |
|---|---|
| `make setup` | One time: create `.venv` and install the pre-commit hook |
| `make install` | Install GNOST and all development tools |
| `make check` | Everything CI runs: lint, format check, tests |
| `make test` | Only the tests |
| `make lint` | Lint with ruff |
| `make format` | Format the code with ruff (it replaces black) |
| `make pre-commit` | Run every pre-commit check on all files |
| `make snapshots` | Regenerate the onboard golden files (review the git diff afterwards) |
| `make docs` / `make docs-open` | Build the documentation (and open it) |
| `make onboard` / `make analyze` | Run GNOST on this repository (`PATH_ARG=some/folder` to change it) |
| `make build` | Build the sdist and wheel |
| `make clean` | Remove build artifacts and caches |

## Development Guidelines
- Keep changes scoped and well-described.
- Maintain a professional, open-source friendly tone in code and docs.
- Prefer small, reviewable commits.
- Avoid formatting churn unrelated to your change.
- Follow core design principles in contribution code:
  - OOP practices (mainly encapsulation),
  - the Open/Closed Principle, and
  - DRY (Don't Repeat Yourself) Principle.

## Architecture Notes
GNOST follows a clear separation of concerns:
- Scanners analyze code
- Core logic builds flow and insights
- Reporters render output (terminal, markdown, diagrams)

`Please avoid mixing analysis logic into reporters or CLI commands.`

## Testing and style
If you add behavior, add or update tests when possible. Run `make check` before you push.
`make format` fixes formatting for you; the formatter is `ruff format` (it is Black-compatible,
so there is no separate black step).

CI uses ruff 0.15.4 (the same version as `.pre-commit-config.yaml`, and what `make install` installs).
A newer ruff on your machine can report different lint results, so if CI disagrees with you, run
`make install` again.

## Documentation
- User-facing changes should update docs or README when needed.
- Longer docs belong in ReadTheDocs instead of README.

## Submitting a PR
- Describe what changed and why.
- Link related issues or discussions if applicable.
- Note any follow-up work or limitations.
- The pull request form asks for these and lists the checks to run (`make check`).

## Code of Conduct
This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By taking part you agree to it.
Be respectful and constructive in all interactions.
