# alertshadow

Test PromQL-backed Grafana-managed provisioning rules offline with Prometheus
`promtool`. The package projects a disposable **test shadow**, then runs your
synthetic-series fixtures. Prefer authoring Prometheus-format rules and importing
them on Grafana 12.1+ where possible; this bridge serves existing native graphs.

Python 3.11–3.13. Runtime dependency: PyYAML only. No network, live queries, parser
subprocess or automatic executable download. Install `promtool` separately to test.

```sh
python -m pip install --require-hashes -r requirements-ci.txt
python -m pytest -q
ruff check alertshadow tests
mypy --strict alertshadow
python -m alertshadow project --root examples
python -m alertshadow test --root examples
python -m build --no-isolation
```

The test command requires `promtool` on PATH; end-to-end pytest cases skip cleanly
when it is absent. CI installs version 2.53.2 and verifies its release checksum.
After a release, install with `pip install alertshadow`; the console script accepts
the same arguments as `python -m alertshadow`.

See [usage](docs/usage.md), [architecture](docs/architecture.md),
[contributing](CONTRIBUTING.md), [security](SECURITY.md), [releases](docs/releases.md)
and [changelog](CHANGELOG.md). Licensed under [Apache-2.0](LICENSE).
No supported public release yet.
