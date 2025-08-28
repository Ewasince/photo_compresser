# AGENTS

## Setup commands
- Install deps: `uv sync`

## Code style
- Format code: `make align_code`
- Use type hints and Python 3.12 features.

## Dev environment tips
- Before run commands first run `source .venv/bin/activate` to use the project environment.

## Testing instructions
- Lint: `make lint.ruff`
- Type-check: `make lint.mypy`
- Tests: `make test.pytest`
- Lint + Type-check + pre-commit commands: `make pre-commit-all`

## Git instructions
- Commit message format: `<type>[optional scope]: <description>`
- Create branches in sub-branch `codex` with sub-branch main, e.g. `codex/<feature-name>/main`
- If creates second PR on same feature create branch `codex/<feature-name>/main2` etc.

## PR instructions
- Title format: `[photo_compresser] <Title>`
- Ensure all lint and test commands pass before submitting.
