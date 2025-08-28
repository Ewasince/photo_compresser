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

## PR instructions
- Title format: `<type>[optional scope]: <Title>`
- Ensure all pre-commit and test commands pass before submitting.
