# Contributing

Thank you for contributing to this repository.

## Development Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running Tests

Run all tests:

```bash
pytest -q
```

Run a specific test group:

```bash
pytest -m unit -q
pytest -m integration -q
pytest -m adversarial -q
```

## Pull Request Process

1. Fork the repository and create a feature branch.
2. Keep changes focused and include tests for new behavior.
3. Ensure `pytest -q` passes locally.
4. Open a pull request using the provided template.

## Style Guidelines

- Keep tests deterministic and isolated.
- Prefer explicit fixtures over implicit state.
- Use clear test names that describe expected behavior.
