import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from research import suite
from research.artifacts import load_archive
from tests.conftest import make_ohlcv


@pytest.fixture
def protocol(tmp_path):
    frame = make_ohlcv(220, trend="up")
    path = tmp_path / "prices.csv"
    frame.to_csv(path, index_label="Date")
    return {"assets": [{"ticker": "TEST", "input": str(path)}], "horizons": [5],
            "test_start": str(frame.index[150]), "as_of": "2026-09-27T00:00:00Z",
            "job_timeout_seconds": 30, "total_timeout_seconds": 60}


def test_suite_runs_real_offline_strategy_worker_and_preserves_inputs(protocol, tmp_path):
    destination = tmp_path / "run"
    summary = suite.run_suite(protocol, destination)
    assert summary["status"] == "completed", summary
    record = summary["jobs"][0]
    assert len(record["result"]["strategies"]) == 4
    saved = load_archive((destination / record["job"] / "result.zip").read_bytes())
    assert saved["manifest"]["kind"] == "strategy_comparison"
    snapshot = load_archive((destination / "input-000.zip").read_bytes())
    pd.testing.assert_frame_equal(snapshot["frames"]["market"], saved["frames"]["market"])
    assert (destination / "protocol.json").is_file()
    with pytest.raises(FileExistsError):
        suite.run_suite(protocol, destination)


@pytest.mark.parametrize("change", [
    {"horizons": [1, 2], "max_jobs": 1}, {"job_timeout_seconds": 0},
    {"total_timeout_seconds": float("nan")}, {"horizons": [True]},
    {"as_of": "2026-09-27"}, {"cost_pct": -1}, {"typo": True},
])
def test_invalid_protocol_rejected_before_artifacts(protocol, tmp_path, change):
    with pytest.raises(ValueError):
        suite.run_suite({**protocol, **change}, tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()


def test_failed_and_timed_out_jobs_are_retained(protocol, tmp_path, monkeypatch):
    outcomes = iter([{"status": "failed", "exit_code": 1}, {"status": "timed_out"}])
    monkeypatch.setattr(suite, "_execute", lambda *args: next(outcomes))
    summary = suite.run_suite({**protocol, "horizons": [1, 5]}, tmp_path / "run")
    assert summary["status"] == "incomplete"
    assert [j["status"] for j in summary["jobs"]] == ["failed", "timed_out"]
    assert len(list((tmp_path / "run").glob("job-*/status.json"))) == 2


def test_cancellation_records_remaining_jobs(protocol, tmp_path, monkeypatch):
    def cancel(*args):
        raise KeyboardInterrupt()
    monkeypatch.setattr(suite, "_execute", cancel)
    summary = suite.run_suite({**protocol, "horizons": [1, 5]}, tmp_path / "run")
    assert [j["status"] for j in summary["jobs"]] == ["cancelled", "cancelled"]


def test_total_budget_prevents_starting_another_job(protocol, tmp_path, monkeypatch):
    clock = [0]
    monkeypatch.setattr(suite.time, "monotonic", lambda: clock[0])
    def timeout(*args):
        clock[0] += 60
        return {"status": "timed_out"}
    monkeypatch.setattr(suite, "_execute", timeout)
    summary = suite.run_suite({**protocol, "horizons": [1, 5]}, tmp_path / "run")
    assert [j["status"] for j in summary["jobs"]] == ["timed_out", "skipped_budget"]


def test_preparation_error_preserves_failure_record(protocol, tmp_path):
    Path(protocol["assets"][0]["input"]).write_text("invalid CSV\n")
    summary = suite.run_suite(protocol, tmp_path / "run")
    assert summary["status"] == "incomplete"
    assert summary["stage"] == "input_preparation"
    assert json.loads((tmp_path / "run" / "summary.json").read_text()) == summary


def test_worker_timeout_kills_process_and_disables_downloads(tmp_path, monkeypatch):
    # Exercise actual process termination without loading weights or waiting on a model.
    original = subprocess.Popen
    children = []
    def sleeper(command, **kwargs):
        assert kwargs["env"]["HF_HUB_OFFLINE"] == "1"
        process = original([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
        children.append(process)
        return process
    monkeypatch.setattr(suite.subprocess, "Popen", sleeper)
    outcome = suite._execute(tmp_path / "job.json", timeout=0.05)
    assert outcome["status"] == "timed_out"
    assert children[0].poll() is not None


def test_forecast_worker_uses_snapshot_and_records_intervals(protocol, tmp_path, monkeypatch):
    from ml.timesfm_runtime import TimesFMRuntime
    from tests.test_timesfm_runtime import FakeTimesFMModel
    # Inject only the optional model; keep the entire worker and archive path real.
    monkeypatch.setattr("ml.timesfm_runtime.TimesFMRuntime",
                        lambda config: TimesFMRuntime(config, model_factory=FakeTimesFMModel))
    def execute(path, timeout):
        suite.run_worker(path)
        return {"status": "completed", "exit_code": 0}
    monkeypatch.setattr(suite, "_execute", execute)
    summary = suite.run_suite({**protocol, "mode": "forecast"}, tmp_path / "run")
    assert summary["status"] == "completed", summary
    result = summary["jobs"][0]["result"]
    assert result["observations"] > 0
    assert result["baseline_metrics"]["last_price"]["mae_improvement_interval"]["status"] == "estimated"
