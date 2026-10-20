from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_INDEX = Path(__file__).resolve().parents[2] / "OpsBench_V2/data/index/pilot10-portable.jsonl"
OPS_COMMIT = "6d61b8bb9c6bc9de6347601562c644fade324765"
FOUND_COMMIT = "5a64aeef63ae84893c644081204b4f9d02e947ae"


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean(v) for v in value]
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def dumps(value):
    return json.dumps(clean(value), ensure_ascii=False, sort_keys=True, allow_nan=False)


def hash_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def evidence(method, modality, kind, subject, observation, selected=True, **extra):
    body = clean(dict(method=method, modality=modality, kind=kind, subject=subject,
                      observation=observation, **extra))
    body["id"] = "e_" + hashlib.sha256(dumps(body).encode()).hexdigest()[:24]
    body["selected"] = bool(selected)
    body["semantics"] = "candidate_observation_not_causal_proof"
    return body


class Dataset:
    """Telemetry input; service_scope is an explicitly privileged offline option."""

    def __init__(self, telemetry: Path, service_scope=None):
        self.root = telemetry
        self.service_scope = set(service_scope) if service_scope is not None else None
        self.cache = {}

    def table(self, window, modality):
        name = f"{window}_{modality}"
        if name not in self.cache:
            path = self.root / (name + ".parquet")
            if path.exists():
                frame = pd.read_parquet(path)
                frame["_source_row"] = np.arange(len(frame))
                if "time" in frame:
                    frame["time"] = pd.to_datetime(frame["time"], utc=True)
                if self.service_scope is not None:
                    mask = frame["service_name"].isin(self.service_scope)
                    if modality.startswith("metrics"):
                        for column in ("attr.source", "attr.destination", "attr.source_workload",
                                       "attr.destination_workload", "attr.k8s.service.name"):
                            if column in frame:
                                mask |= frame[column].isin(self.service_scope)
                    frame = frame[mask].copy()
                self.cache[name] = frame
            else:
                self.cache[name] = pd.DataFrame()
        return self.cache[name]

    def metric_series(self):
        for modality in ("metrics", "metrics_sum"):
            frames = []
            for window in ("normal", "abnormal"):
                frame = self.table(window, modality)
                if not frame.empty:
                    frames.append(frame.assign(_window=window))
            if not frames:
                continue
            frame = pd.concat(frames, ignore_index=True)
            dims = sorted(c for c in frame if c not in ("time", "value", "_source_row", "_window"))
            for values, group in frame.groupby(dims, dropna=False, sort=True):
                if not isinstance(values, tuple):
                    values = (values,)
                subject = {k: None if pd.isna(v) else v for k, v in zip(dims, values)}
                subject["modality"] = modality
                yield subject, group.sort_values(["time", "_window", "_source_row"])

    def provenance(self):
        return {p.name: {"sha256": hash_file(p), "bytes": p.stat().st_size}
                for p in sorted(self.root.glob("*.parquet"))}


def series_rows(group):
    return [{"window": r["_window"], "row": int(r["_source_row"]),
             "time": r["time"], "value": r["value"]}
            for r in group.to_dict("records")]


def subject_services(subject):
    values = [subject.get("service_name"), subject.get("attr.k8s.service.name")]
    values += [subject.get(k) for k in ("attr.source", "attr.destination",
                                       "attr.source_workload", "attr.destination_workload")]
    return sorted({v for v in values if isinstance(v, str) and v})
