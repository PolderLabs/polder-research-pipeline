# Contributing

Thanks for helping improve Polder Research Pipeline. Contributions are welcome through GitHub issues and pull requests.

The supported runtime and test environment is Python 3.14 or newer, as declared
in `pyproject.toml`. CI also compiles the source, scripts, and tests with
Python 3.13 as a syntax-compatibility guard; this parse check does not make
Python 3.13 a supported runtime.

## Before opening a pull request

- Describe the user-facing behavior or defect and the evidence for the change.
- Keep changes focused; do not include `.research/`, raw research material, credentials, model weights, or machine-local editor state.
- Add or update tests and documentation when behavior or workflow contracts change.
- Run the same checks as CI from the repository root:

  ```sh
  python -m pip install -r requirements-ci.txt
  python -m pip install -e .
  ruff check .
  ruff format --check .
  PYTHONPATH=src pytest -q
  python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py
  python3 scripts/generate_derived.py
  git diff --check
  ```

- Keep provider credentials out of commits and test fixtures. Use synthetic or public material in examples.
- Treat changes to schemas, authority boundaries, persistence, classification, and research-method gates as compatibility-sensitive; explain migration and validation evidence.

CI must pass before merge. Reviews of research-method changes should distinguish software correctness from the validity and completeness of the underlying evidence.
