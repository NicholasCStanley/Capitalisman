"""Tests for the TimesFM runtime adapter without loading model weights."""

import numpy as np
import pytest
import os
import sys
from types import SimpleNamespace

from ml.timesfm_runtime import (
    TimesFMRuntime,
    TimesFMRuntimeConfig,
    probability_above,
    ForecastCancelled,
)

REAL_LOAD = TimesFMRuntime.load  # production path is tested only with fake dependency modules


class FakeTimesFMModel:
    def forecast(self, horizon, inputs):
        point = np.stack([
            np.linspace(values[-1], values[-1] * 1.05, horizon) for values in inputs
        ])
        quantiles = np.zeros((len(inputs), horizon, 10))
        quantiles[:, :, 0] = point
        for quantile_idx in range(1, 10):
            quantiles[:, :, quantile_idx] = point * (
                0.90 + quantile_idx * 0.02
            )
        return point, quantiles


def test_forecast_parses_point_and_quantiles():
    runtime = TimesFMRuntime(model_factory=FakeTimesFMModel)
    result = runtime.forecast([np.arange(1, 101, dtype=float)], horizon=5)[0]
    assert result.point.shape == (5,)
    assert result.quantiles[0.1].shape == (5,)
    assert result.terminal_quantile(0.1) < result.terminal_quantile(0.9)
    assert result.horizon == 5


def test_probability_above_uses_terminal_distribution():
    runtime = TimesFMRuntime(model_factory=FakeTimesFMModel)
    result = runtime.forecast([np.arange(1, 101, dtype=float)], horizon=5)[0]
    low_threshold = result.terminal_quantile(0.2)
    high_threshold = result.terminal_quantile(0.8)
    assert probability_above(result, low_threshold) > probability_above(
        result, high_threshold
    )


def test_rejects_horizon_above_compiled_maximum():
    runtime = TimesFMRuntime(
        TimesFMRuntimeConfig(max_horizon=4), model_factory=FakeTimesFMModel
    )
    with pytest.raises(ValueError, match="Horizon must be"):
        runtime.forecast([np.arange(20)], horizon=5)


def test_rejects_unexpected_model_shapes():
    class BadModel:
        def forecast(self, horizon, inputs):
            return np.zeros((1, 1)), np.zeros((1, 1, 1))

    runtime = TimesFMRuntime(model_factory=BadModel)
    with pytest.raises(RuntimeError, match="Unexpected point forecast shape"):
        runtime.forecast([np.arange(40)], horizon=5)


def test_config_reads_environment(monkeypatch):
    monkeypatch.setenv("CAPITALISMAN_TIMESFM_DEVICE", "cuda")
    monkeypatch.setenv("CAPITALISMAN_TIMESFM_BATCH_SIZE", "8")
    config = TimesFMRuntimeConfig.from_environment()
    assert config.device == "cuda"
    assert config.batch_size == 8


def test_model_cannot_mutate_adapter_batch_size():
    class PaddingModel(FakeTimesFMModel):
        def forecast(self, horizon, inputs):
            original = super().forecast(horizon, inputs)
            inputs.extend([np.zeros(3)] * 4)
            return original

    runtime = TimesFMRuntime(model_factory=PaddingModel)
    results = runtime.forecast([np.arange(40)], horizon=3)
    assert len(results) == 1


def test_forecast_uses_selected_context_length():
    seen_lengths = []

    class RecordingModel(FakeTimesFMModel):
        def forecast(self, horizon, inputs):
            seen_lengths.extend(len(values) for values in inputs)
            return super().forecast(horizon, inputs)

    runtime = TimesFMRuntime(
        TimesFMRuntimeConfig(
            max_context=256, forecast_context=64, chunk_size=2
        ),
        model_factory=RecordingModel,
    )
    runtime.forecast([np.arange(200)] * 3, horizon=3)
    assert seen_lengths == [64, 64, 64]


def test_forecast_rejects_non_finite_inputs():
    values = np.arange(40, dtype=float)
    values[-1] = np.nan
    runtime = TimesFMRuntime(model_factory=FakeTimesFMModel)
    with pytest.raises(ValueError, match="NaN or infinite"):
        runtime.forecast([values], horizon=3)


def test_forecast_chunks_large_calls():
    calls = []

    class RecordingModel(FakeTimesFMModel):
        def forecast(self, horizon, inputs):
            calls.append(len(inputs))
            return super().forecast(horizon, inputs)

    runtime = TimesFMRuntime(
        TimesFMRuntimeConfig(chunk_size=2), model_factory=RecordingModel
    )
    results = runtime.forecast([np.arange(40)] * 5, horizon=3)
    assert len(results) == 5
    assert calls == [2, 2, 1]


@pytest.fixture
def fake_dependencies(monkeypatch):
    class Device(str):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class Upstream(FakeTimesFMModel):
        def __init__(self, **kwargs):
            # Reproduce upstream's implicit CUDA selection before checkpoint load.
            self.model = SimpleNamespace(device=Device("cuda:0"), device_count=8)

        @classmethod
        def from_pretrained(cls, model_id, **kwargs):
            instance = cls(**kwargs)
            tensor = SimpleNamespace(device=instance.model.device)
            instance.model.parameters = lambda: iter([tensor])
            instance.model.buffers = lambda: iter([])
            return instance

        def compile(self, config):
            self.compiled_device_count = self.model.device_count

    cuda = SimpleNamespace(is_available=lambda: True, get_device_name=lambda _: "fake GPU",
                           get_device_properties=lambda _: SimpleNamespace(total_memory=8 * 1024**3),
                           mem_get_info=lambda _: (6 * 1024**3, 8 * 1024**3), empty_cache=lambda: None)
    torch = SimpleNamespace(device=Device, __version__="fake", version=SimpleNamespace(cuda="fake"), cuda=cuda)
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "timesfm", SimpleNamespace(TimesFM_2p5_200M_torch=Upstream,
                                                              ForecastConfig=lambda **kwargs: kwargs))
    monkeypatch.setattr("ml.timesfm_runtime.metadata.version", lambda _: "2.0.2")
    monkeypatch.setattr(TimesFMRuntime, "_available_ram_gb", staticmethod(lambda: 8))
    monkeypatch.setattr("ml.timesfm_runtime.shutil.disk_usage", lambda _: SimpleNamespace(free=8 * 1024**3))
    return torch


def test_device_switches_bind_before_checkpoint_and_leave_environment_unchanged(fake_dependencies, monkeypatch):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0,1")
    for device, expected in (("cpu", "cpu"), ("cuda", "cuda:0"), ("cpu", "cpu")):
        runtime = TimesFMRuntime(TimesFMRuntimeConfig(device=device))
        runtime.load = REAL_LOAD.__get__(runtime)
        runtime.forecast([np.arange(40)], 3)
        assert runtime.status.model_device == expected
        assert runtime._model.compiled_device_count == 1
        assert runtime.preflight().state == "loaded"
        assert os.environ["CUDA_VISIBLE_DEVICES"] == "0,1"
        runtime.unload()
        assert runtime._model is None


def test_explicit_unavailable_cuda_does_not_fall_back(fake_dependencies):
    fake_dependencies.cuda.is_available = lambda: False
    runtime = TimesFMRuntime(TimesFMRuntimeConfig(device="cuda"))
    with pytest.raises(RuntimeError, match="CUDA was requested"):
        REAL_LOAD(runtime)
    assert runtime.status.state == "unavailable"
    assert runtime._model is None


def test_tensor_device_mismatch_is_rejected_before_inference(fake_dependencies):
    runtime = TimesFMRuntime(TimesFMRuntimeConfig(device="cpu"))
    runtime.load = REAL_LOAD.__get__(runtime)
    runtime.load()
    next(runtime._model.model.parameters()).device = "cuda:0"
    with pytest.raises(RuntimeError, match="device mismatch"):
        runtime.forecast([np.arange(40)], 3)


def test_oom_releases_model_and_returns_no_partial_results():
    calls = []

    class OOMModel(FakeTimesFMModel):
        def forecast(self, horizon, inputs):
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError("CUDA out of memory")
            return super().forecast(horizon, inputs)

    runtime = TimesFMRuntime(TimesFMRuntimeConfig(chunk_size=1), model_factory=OOMModel)
    with pytest.raises(RuntimeError, match="Reduce batch/chunk size"):
        runtime.forecast([np.arange(40)] * 3, 3)
    assert len(calls) == 2
    assert runtime.status.state == "out_of_memory"
    assert runtime._model is None


def test_cancellation_before_load_and_between_chunks():
    runtime = TimesFMRuntime(TimesFMRuntimeConfig(chunk_size=1), model_factory=FakeTimesFMModel)
    with pytest.raises(ForecastCancelled):
        runtime.forecast([np.arange(40)], 3, cancel_check=lambda: True)
    assert runtime._model is None
    checks = iter([False, False, True])
    with pytest.raises(ForecastCancelled):
        runtime.forecast([np.arange(40)] * 2, 3, cancel_check=lambda: next(checks))
    assert runtime.status.state == "cancelled"
    assert len(runtime.forecast([np.arange(40)], 3)) == 1
    assert runtime.status.state == "loaded"


def test_replacing_singleton_unloads_old_runtime(monkeypatch):
    import ml.timesfm_runtime as module
    old = TimesFMRuntime(model_factory=FakeTimesFMModel)
    old.load()
    monkeypatch.setattr(module, "_runtime", old)
    new = module.get_timesfm_runtime(TimesFMRuntimeConfig(device="cpu"))
    assert new is not old
    assert old._model is None
