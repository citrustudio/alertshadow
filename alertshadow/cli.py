"""Command-line interface; no network or promtool installation."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
from typing import Any

import yaml

from .core import Invalid, project_files


def run_tests(root: Path, config: dict[str, Any], files: list[Path]) -> None:
    executable = shutil.which("promtool")
    if executable is None:
        raise Invalid("promtool is required on PATH; install it explicitly")
    fixtures = sorted({path for pattern in config.get("fixtures", []) for path in root.glob(pattern)})
    if not fixtures:
        raise Invalid("no test fixtures matched")
    for args in (["check", "rules", *map(str, files)], ["test", "rules", *map(str, fixtures)]):
        subprocess.run([executable, *args], cwd=root, check=True, timeout=120)
    projected = {r["alert"] for p in files for g in yaml.safe_load(p.read_text())["groups"] for r in g["rules"]}
    tested = {a["alertname"] for p in fixtures for t in yaml.safe_load(p.read_text()).get("tests", []) for a in t.get("alert_rule_test", [])}
    print(f"coverage: {len(projected & tested)}/{len(projected)} projected alert names have assertions")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["project", "test"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("alertshadow.toml"))
    parser.add_argument("--no-project", action="store_true", help="test existing marker-owned shadows")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        with (root / args.config).open("rb") as stream:
            config = tomllib.load(stream)
        if args.no_project:
            if args.command != "test":
                raise Invalid("--no-project requires test")
            out = (root / config.get("out", "generated")).resolve()
            if root not in out.parents:
                raise Invalid("output must be strictly inside root")
            from .core import HEADER
            files = [p for p in out.rglob("*") if p.is_file() and not p.is_symlink() and p.read_bytes().startswith(HEADER.encode())]
            if not files:
                raise Invalid("no marker-owned shadows")
        else:
            files = project_files(root, config)
        if args.command == "test":
            run_tests(root, config, files)
        return 0
    except (Invalid, OSError, ValueError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
        print(f"alertshadow: {exc}", file=sys.stderr)
        return 1
