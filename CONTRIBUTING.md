# Contributing to MediClear AI

Thank you for your interest in contributing! MediClear AI is an open-source project welcoming improvements of all kinds.

## How to contribute

### Reporting bugs

Open an issue on GitHub with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behaviour
- Your environment (OS, Python version, AI provider)

### Suggesting features

Open an issue with the `enhancement` label and describe the feature and the use case it addresses.

### Submitting a pull request

1. **Fork** the repository and create a branch: `git checkout -b feature/my-feature`
2. **Install** everything: `pip install '.[all,ocr,tts-local,dev]'`
3. **Make your changes** following the code style below
4. **Run the quality gate** (all must pass - CI runs the same):
   ```bash
   ruff check app/ tests/
   ruff format --check app/ tests/
   mypy app/
   pytest -q
   ```
5. **Open a PR** against `master` with a clear description of what changed and why

## Code style

- Python 3.11+, type annotations on all public functions
- `from __future__ import annotations` at the top of every module
- `ruff` for linting + formatting, `mypy` for type checking (config in `pyproject.toml`)
- Follow the existing layered architecture (see [docs/architecture.md](docs/architecture.md))
- No hardcoded model names, API keys, or provider assumptions
- All new configuration must be a Pydantic Settings field in `app/config.py`

## Adding a new AI provider

Providers are thin - implement one primitive and the base class does the rest:

1. Create `app/providers/your_provider.py` subclassing `BaseAIProvider` and
   implement `_complete` (and optionally `_stream`), plus the identity properties.
2. Register it in `build_single_provider()` in `app/providers/registry.py`.
3. Add the provider name literal to `ai_provider` in `app/config.py`.
4. Add an optional-dependency extra in `pyproject.toml` if it needs an SDK.
5. Add example configuration to `.env.example` and the docs.
6. Add at least a basic test.

## Medical content guidelines

MediClear AI is used in healthcare settings. All AI system prompt changes must:
- Maintain clear disclaimers that the tool is not a substitute for medical advice
- Not introduce language that could be interpreted as a diagnosis or treatment recommendation
- Be reviewed carefully before merging

## License

By contributing, you agree your contributions will be licensed under the MIT License.
