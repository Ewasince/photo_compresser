# AGENTS

## Setup commands
- Install deps: `uv sync`

## Code style
- Format code: `uv run ruff format .`
- Use type hints and Python 3.12 features.

## Dev environment tips
- Run commands through `uv run` to use the project environment.

## Testing instructions
- Lint: `uv run ruff check . --fix`
- Type-check: `uv run mypy`
- Tests: `uv run pytest`

## PR instructions
- Title format: `[photo_compresser] <Title>`
- Ensure all lint and test commands pass before submitting.
