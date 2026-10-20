import numpy as np
import pandas as pd
import pytest

from rca_processing.alignment import align, dimacs
from rca_processing.common import evidence
from rca_processing.foundroot import extract


class SeriesData:
    def metric_series(self):
        for name, values in [("spike", [9., 10., 11., 50.]), ("flat", [0., 0., 0., 5.])]:
            frame = pd.DataFrame({
                "value": values, "_window": ["normal"] * 3 + ["abnormal"],
                "time": pd.date_range("2025-01-01", periods=4, tz="UTC"),
                "_source_row": [0, 1, 2, 0],
            })
            yield {"metric": name, "service_name": "a"}, frame


def test_foundroot_baseline_and_zero_variance():
    records, _ = extract(SeriesData())
    assert records[0]["selected"]
    assert not records[1]["selected"]
    assert records[1]["observation"]["verdict"] == "insufficient_baseline"


def test_path_association_is_not_causal_proof():
    graph = {"nodes": [{"component": "service|a"}, {"component": "service|b"}],
             "edges": [{"source": "service|a", "target": "service|b"}],
             "root_causes": [{"component": "service|a"}]}
    record = evidence("opsagent", "trace", "high_latency_window", {"service_name": "a"},
                      {"events": [{"caller": "b"}]})
    phi = align([record], graph)
    assert phi["summary"]["candidate_associated"] == 3
    assert phi["summary"]["covered"] == 0
    assert dimacs(phi)[0] == "p cnf 0 4\n0\n0\n0\n0\n"
    phi = align([record], graph, {"dependency:a->b": {record["id"]: "supports"}})
    assert phi["summary"]["covered"] == 1
    with pytest.raises(ValueError):
        align([record], graph, {"node:a": {"unknown": "supports"}})


def test_shape_checkpoint_inference():
    from pathlib import Path
    checkpoint = Path(__file__).resolve().parents[1] / "assets/patterncla.pt"
    if not checkpoint.exists():
        pytest.skip("Optional external shape checkpoint not downloaded")
    pytest.importorskip("torch")
    from rca_processing.shapes import ShapeClassifier, LABELS
    model = ShapeClassifier(checkpoint)
    assert model.predict(np.arange(30)) in LABELS
    assert model.predict(np.zeros(30)) is None


def test_opsagent_trace_parent_identity_and_fast_failure_exclusion():
    from rca_processing.opsagent import trace_features
    rows = []
    for trace in range(100):
        # Reused span IDs across traces must not cross-link different services.
        rows += [
            {"trace_id": str(trace), "span_id": "parent", "parent_span_id": "",
             "service_name": "b" if trace == 99 else "unrelated", "span_name": "entry",
             "attr.span_kind": "Server", "duration": 2000000,
             "time": pd.Timestamp("2025-01-01", tz="UTC"), "_source_row": trace * 2},
            {"trace_id": str(trace), "span_id": "child", "parent_span_id": "parent",
             "service_name": "a", "span_name": "call", "attr.span_kind": "Server",
             "duration": 1000000 if trace == 99 else 100,
             "time": pd.Timestamp("2025-01-01", tz="UTC"), "_source_row": trace * 2 + 1},
        ]
    class Data:
        def table(self, *_):
            return pd.DataFrame(rows)
    records = trace_features(Data())
    assert len(records) == 1
    assert records[0]["observation"]["callers"] == {"b": 1}
    assert records[0]["observation"]["max_latency_ms"] == 1
    assert records[0]["observation"]["count"] == 1


def test_opsagent_drain_and_keyword_filter():
    from rca_processing.opsagent import log_features
    class Data:
        def table(self, *_):
            return pd.DataFrame({
                "time": pd.to_datetime(["2025-01-01T00:00:00Z"] * 4),
                "_source_row": range(4), "service_name": ["a"] * 4,
                "message": ["normal request", "error connection 123", "error connection 124",
                            "fatal crash exception"],
            })
    records = log_features(Data())
    assert records
    assert all("normal request" != r["observation"]["message"] for r in records)
    assert any(r["selected"] for r in records)


def test_opsagent_empty_modalities_are_explicit():
    from rca_processing.opsagent import log_features, trace_features
    class Data:
        def table(self, *_):
            return pd.DataFrame()
    assert log_features(Data()) == trace_features(Data()) == []


def test_path_scope_keeps_row_provenance_and_metric_endpoints(tmp_path):
    from rca_processing.common import Dataset
    frame = pd.DataFrame({
        "service_name": ["a", "collector", "elsewhere"],
        "attr.destination": [None, "a", "z"],
        "metric": ["cpu"] * 3, "value": [1., 2., 3.],
        "time": pd.date_range("2025-01-01", periods=3, tz="UTC"),
    })
    frame.to_parquet(tmp_path / "abnormal_metrics.parquet")
    result = Dataset(tmp_path, {"a"}).table("abnormal", "metrics")
    assert result["_source_row"].tolist() == [0, 1]
    assert Dataset(tmp_path).table("abnormal", "metrics").shape[0] == 3
