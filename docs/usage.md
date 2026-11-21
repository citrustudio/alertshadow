# Usage

`alertshadow [-h] {project,test} [--root DIR] [--config FILE] [--no-project]`.
`-h` / `--help` shows help. `--root` defaults to the current directory; relative
`--config` defaults to `alertshadow.toml` inside root. Exit 0 means success; exit 1
means invalid input, missing executable, timeout or failed promtool validation.
Argparse uses exit 2 for invalid command syntax.

Configuration is TOML, with the complete example in `examples/alertshadow.toml`:

- `rules`: nonempty relative rule globs; no absolute paths or parent traversal.
- `out`: shadow directory, default `generated`, strictly beneath root. Input files
  must be outside it. Do not use it for your own files or provision its contents.
- `fixtures`: relative promtool fixture globs, required by `test`.
- `strict`: default true. Unsupported rules fail; false prints skip reasons.
  Parse errors always fail, and projecting zero files always fails.
- `env`: names of environment variables to expand as `$NAME` or `${NAME}` in YAML.
  Names must be valid and set. Other placeholders stay literal. Values must form
  valid YAML; treat config and environment as trusted inputs.
- `[datasources]`: datasource UID keys mapped to `prometheus` or `skip`. Unknown
  UIDs fail in strict mode, never guessed from a name.

`project` supports one-query classic conditions using last reduction and one
comparison, direct reduce-last → threshold, one-query math comparisons against a
number, and directly filtering query conditions. Operators are gt/lt/gte/lte;
math uses >, <, >=, <=. Multiple queries, unsupported reducers, compound math,
missing/duplicate references, unknown datasources, multiple conditions, empty
queries and non-finite thresholds are rejected or explicitly skipped.
Native Kubernetes `PrometheusRule` alert groups pass through; recording rules are
reported unsupported. Alert names, expressions, `for` and labels survive.

Each output keeps the source-relative path: `rules/value.yaml` becomes
`generated/rules/value.yaml`. A fixture in `fixtures/` references it as
`../generated/rules/value.yaml`. `test` projects, checks every shadow with
`promtool check rules`, runs `promtool test rules` and reports distinct alert-name
assertion coverage. An empty fixture match fails. Each subprocess has a 120-second
deadline. `test --no-project` uses existing marker-owned shadows, enabling an
external projection step; it fails if none exist.

Only files bearing the exact generator header may be overwritten or removed as
stale. Other files are preserved; collisions and symlinks fail before writes.
Rules are limited to 8 MiB each. A failed parse or projection leaves existing
outputs intact. Keep fixture evaluation intervals consistent with Grafana groups.
