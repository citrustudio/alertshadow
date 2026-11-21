# Local development

See the [organization contribution policy](https://github.com/citrustudio/.github/blob/main/CONTRIBUTING.md)
for pull requests, review, DCO and AI disclosure.

Run `python -m pytest -q`, `ruff check alertshadow tests` and `mypy --strict alertshadow`.
Install hash-locked build/test tools with `python -m pip install --require-hashes -r requirements-ci.txt`.
Build with `python -m build --no-isolation`.
