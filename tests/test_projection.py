from copy import deepcopy
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from alertshadow.core import HEADER, Invalid, project_files, project_rule
from alertshadow.cli import main, run_tests

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def rule():
    return yaml.safe_load((EXAMPLES / "rules/value.yaml").read_text())["groups"][0]["rules"][0]


def test_classic_value_not_presence(rule):
    result = project_rule(rule, {"metrics": "prometheus"})
    assert result == {"alert": "ValueAlert", "expr": "(service_ready == bool 0) > 0", "for": "2m", "labels": {"severity": "warning"}}


def test_threshold(rule):
    rule["data"].insert(1, {"refId": "R", "datasourceUid": "__expr__", "model": {"type": "reduce", "reducer": "last", "expression": "A"}})
    rule["data"][-1]["model"].update(type="threshold", expression="R")
    assert project_rule(rule, {"metrics": "prometheus"})["expr"].endswith("> 0")
    rule["data"][1]["model"]["reducer"] = "mean"
    with pytest.raises(Invalid, match="reduce-last"):
        project_rule(rule, {"metrics": "prometheus"})


def test_math(rule):
    rule["data"][-1]["model"] = {"type": "math", "expression": "$A >= 2e-3"}
    assert project_rule(rule, {"metrics": "prometheus"})["expr"].endswith(">= 2e-3")
    rule["data"][-1]["model"]["expression"] = "$A > 1 && $C > 1"
    with pytest.raises(Invalid, match="math"):
        project_rule(rule, {"metrics": "prometheus"})


@pytest.mark.parametrize("mode", [None, "skip"])
def test_datasource_skip(rule, mode):
    with pytest.raises(Invalid, match="datasource"):
        project_rule(rule, {} if mode is None else {"metrics": mode})


def test_unsupported(rule):
    for mutation in ("multi", "count", "reference", "duplicate"):
        other = deepcopy(rule)
        if mutation == "multi":
            other["data"].append({"refId": "C", "datasourceUid": "metrics", "model": {"expr": "up"}})
        elif mutation == "count":
            other["data"][-1]["model"]["conditions"] *= 2
        elif mutation == "reference":
            other["data"][-1]["model"]["conditions"][0]["query"]["params"] = ["X"]
        else:
            other["data"].append(other["data"][0])
        with pytest.raises(Invalid):
            project_rule(other, {"metrics": "prometheus"})


def setup_tree(tmp_path):
    shutil.copytree(EXAMPLES, tmp_path, dirs_exist_ok=True, ignore=shutil.ignore_patterns("generated"))
    return {"rules": ["rules/*.yaml"], "out": "generated", "datasources": {"metrics": "prometheus"}, "fixtures": ["fixtures/*.yaml"]}


def test_native_and_same_basename(tmp_path):
    native = {"kind": "PrometheusRule", "spec": {"groups": [{"name": "native", "rules": [{"alert": "Native", "expr": "up < 1"}]}]}}
    for folder in ("one", "two"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "rules.yaml").write_text(yaml.safe_dump(native))
    result = project_files(tmp_path, {"rules": ["*/rules.yaml"]})
    assert {p.relative_to(tmp_path).as_posix() for p in result} == {"generated/one/rules.yaml", "generated/two/rules.yaml"}


def test_parse_failure_never_silent(tmp_path):
    config = setup_tree(tmp_path)
    source = tmp_path / "rules/value.yaml"
    for content in ("groups: [", "!!python/object/apply:os.system ['echo forbidden']", "null"):
        source.write_text(content)
        with pytest.raises(Invalid):
            project_files(tmp_path, {**config, "strict": False})
    assert not (tmp_path / "generated").exists()


def test_owned_cleanup_and_preflight(tmp_path):
    config = setup_tree(tmp_path)
    outputs = project_files(tmp_path, config)
    keep = tmp_path / "generated/keep.txt"
    keep.write_text("user text")
    stale = tmp_path / "generated/stale.yaml"
    stale.write_text(HEADER + "groups: []")
    project_files(tmp_path, config)
    assert keep.read_text() == "user text" and not stale.exists()
    outputs[0].write_text("unowned")
    with pytest.raises(Invalid, match="unowned"):
        project_files(tmp_path, config)
    assert outputs[0].read_text() == "unowned"


@pytest.mark.parametrize("out", [".", "../outside"])
def test_unsafe_out(tmp_path, out):
    config = setup_tree(tmp_path)
    with pytest.raises(Invalid):
        project_files(tmp_path, {**config, "out": out})


def test_symlink(tmp_path):
    config = setup_tree(tmp_path)
    (tmp_path / "generated").symlink_to(tmp_path / "rules", target_is_directory=True)
    with pytest.raises(Invalid):
        project_files(tmp_path, config)


def test_environment(tmp_path, monkeypatch):
    config = setup_tree(tmp_path)
    source = tmp_path / "rules/value.yaml"
    source.write_text(source.read_text().replace("service_ready", "${METRIC}"))
    monkeypatch.setenv("METRIC", "example_ready")
    outputs = project_files(tmp_path, {**config, "env": ["METRIC"]})
    assert "example_ready" in outputs[0].read_text()


def test_nonstrict_report(tmp_path, capsys):
    config = setup_tree(tmp_path)
    doc = yaml.safe_load((tmp_path / "rules/value.yaml").read_text())
    other = deepcopy(doc["groups"][0]["rules"][0])
    other["data"][0]["datasourceUid"] = "logs"
    doc["groups"][0]["rules"].append(other)
    (tmp_path / "rules/value.yaml").write_text(yaml.safe_dump(doc))
    project_files(tmp_path, {**config, "strict": False})
    assert "skipped" in capsys.readouterr().out


def test_runner_errors(tmp_path, monkeypatch):
    config = setup_tree(tmp_path)
    files = project_files(tmp_path, config)
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(Invalid, match="required"):
        run_tests(tmp_path, config, files)
    monkeypatch.setattr(shutil, "which", lambda _: "promtool")
    with pytest.raises(Invalid, match="no test"):
        run_tests(tmp_path, {**config, "fixtures": []}, files)
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        run_tests(tmp_path, config, files)


def test_cli(tmp_path):
    setup_tree(tmp_path)
    assert main(["project", "--root", str(tmp_path)]) == 0


@pytest.mark.skipif(shutil.which("promtool") is None, reason="promtool is not installed")
def test_promtool_end_to_end(tmp_path):
    config = setup_tree(tmp_path)
    run_tests(tmp_path, config, project_files(tmp_path, config))


@pytest.mark.parametrize("fixture", sorted((Path(__file__).parent / "fixtures").glob("*.yaml")))
def test_neutral_fixture_contract(fixture):
    rule = yaml.safe_load(fixture.read_text())
    if fixture.stem.startswith("skip-"):
        with pytest.raises(Invalid):
            project_rule(rule, {"metrics": "prometheus", "logs": "skip"})
    else:
        result = project_rule(rule, {"metrics": "prometheus"})
        assert result["alert"] == fixture.stem
        assert result["for"] == rule["for"]
        assert result["labels"] == rule["labels"]


def test_output_symlink_ancestor(tmp_path):
    config = setup_tree(tmp_path)
    (tmp_path / "actual").mkdir()
    (tmp_path / "link").symlink_to(tmp_path / "actual", target_is_directory=True)
    with pytest.raises(Invalid):
        project_files(tmp_path, {**config, "out": "link/generated"})


@pytest.mark.skipif(shutil.which("promtool") is None, reason="promtool is not installed")
def test_missing_value_fold_is_red(tmp_path):
    config = setup_tree(tmp_path)
    files = project_files(tmp_path, config)
    files[0].write_text(files[0].read_text().replace('(service_ready == bool 0) > 0', 'service_ready == bool 0'))
    with pytest.raises(subprocess.CalledProcessError):
        run_tests(tmp_path, config, files)


@pytest.mark.skipif(shutil.which("promtool") is None, reason="promtool is not installed")
def test_existing_shadows_cli(tmp_path):
    setup_tree(tmp_path)
    assert main(["project", "--root", str(tmp_path)]) == 0
    assert main(["test", "--no-project", "--root", str(tmp_path)]) == 0


@pytest.mark.parametrize("kind", ["classic_conditions", "threshold"])
def test_threshold_precision(rule, kind):
    if kind == "threshold":
        rule["data"].insert(1, {"refId": "R", "datasourceUid": "__expr__", "model": {"type": "reduce", "reducer": "last", "expression": "A"}})
        rule["data"][-1]["model"].update(type="threshold", expression="R")
    rule["data"][-1]["model"]["conditions"][0]["evaluator"]["params"] = [0.123456789]
    expr = project_rule(rule, {"metrics": "prometheus"})["expr"]
    threshold = float(expr.rsplit(" ", 1)[1])
    assert threshold == 0.123456789
    assert 0.1234568 > threshold
