#!/usr/bin/env bash
# CI-only installer; the CLI never downloads executables.
set -euo pipefail
version=2.53.2
archive="prometheus-${version}.linux-amd64.tar.gz"
base="https://github.com/prometheus/prometheus/releases/download/v${version}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cd "$work"
curl --fail --location --max-time 180 --output "$archive" "$base/$archive"
curl --fail --location --max-time 60 --output sha256sums.txt "$base/sha256sums.txt"
awk -v file="$archive" '$2 == file {print}' sha256sums.txt > selected.sha256
test -s selected.sha256
sha256sum --check selected.sha256
tar -xzf "$archive" "prometheus-${version}.linux-amd64/promtool"
install -m 755 "prometheus-${version}.linux-amd64/promtool" "$1/promtool"
