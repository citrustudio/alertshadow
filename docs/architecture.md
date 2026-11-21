# Architecture

The CLI reads TOML, the core parses provisioning YAML with `yaml.safe_load`, then
projects a conservative subset of expression graphs. It emits YAML through
PyYAML, preserving source-relative paths and an ownership header. All inputs are
projected before output preflight and mutation. Cleanup unlinks only marked stale
files and never removes a directory tree. Source or output symlink traversal is
refused. The root is an explicit caller-selected workspace trust boundary.

Grafana tests sample **values**, while Prometheus alert rules fire on series
**presence**. Every evaluator is folded into the query, even when it already has a
comparison: `(service_ready == bool 0) > 0` excludes healthy zero-valued samples.
Reduce-last/threshold and simple math have equivalent explicit projections.
The runner only invokes the installed promtool, with argument arrays and a deadline.

This is deliberately lossy: annotations, group intervals, NoData/execErrState,
Grafana templating and live datasource behavior are not reproduced. Multi-query,
compound expressions and non-last reductions are rejected rather than guessed.
It is not a Grafana evaluator or a rule linter. Passing fixtures prove only the
projected PromQL at the tested series, thresholds, labels and pending duration.
The private canary-analysis converters are not part of this package.
