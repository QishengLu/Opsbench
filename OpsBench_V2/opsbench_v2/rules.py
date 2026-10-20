"""Frozen pilot heuristics. Never inferred from case labels or injection metadata."""
VERSION = "1.0.0"
CONTRACT = {
    "version": VERSION,
    "min_samples": 5,
    "min_events": 3,
    "latency_ratio": 3.0,
    "latency_delta_ms": 20.0,
    "error_rate_delta": 0.05,
    "error_rate_ratio": 2.0,
    "log_rate_delta": 0.01,
    "log_rate_ratio": 3.0,
    "metric_ratio": 3.0,
    "cpu_delta": 0.5,
    "nested_min_ms": 20.0,
    "nested_min_fraction_of_caller": 0.5,
    "nested_min_fraction_of_pairs": 0.5,
    "lifecycle_restart_delta": 1,
    "lifecycle_ready_ratio": 0.5,
    "semantics": "Exploratory fixed heuristics; not calibrated detection guarantees.",
}
LOG_PATTERNS = {
    "connection_failure": r"(?i)(cannot|could not|unable to|failed to).*?(connection|connect)|connection.*?(refused|reset|timed out)|communications link failure|hikaripool.*?(timeout|not available)",
    "timeout": r"(?i)timeout|timed out",
    "dns_failure": r"(?i)unknownhostexception|name or service not known|temporary failure in name resolution",
    "response_parse_failure": r"(?i)jsonparseexception|jsonmappingexception|unrecognized token|unexpected character|httpmessagenotreadableexception",
    "application_exception": r"(?i)nullpointerexception|incorrectresultsizedataaccessexception|illegalstateexception|illegalargumentexception",
    "error_message": r"(?i)\bexception\b|\berror\b|\bfailed\b|\bfailure\b",
    "startup_message": r"(?i)starting .*application|started .*application|jvm running for",
}


def increased_latency(normal, abnormal, field="median_ms"):
    if not normal or not abnormal or min(normal["n"], abnormal["n"]) < CONTRACT["min_samples"]:
        return "insufficient"
    b, a = normal.get(field), abnormal.get(field)
    if b is None or a is None:
        return "insufficient"
    return "supports" if a >= max(b * CONTRACT["latency_ratio"], b + CONTRACT["latency_delta_ms"]) else "not_met"


def increased_rate(normal, abnormal, field="errors", log=False):
    if not normal or not abnormal or min(normal["n"], abnormal["n"]) < CONTRACT["min_samples"]:
        return "insufficient"
    b, a = normal[field] / normal["n"], abnormal[field] / abnormal["n"]
    delta = CONTRACT["log_rate_delta" if log else "error_rate_delta"]
    ratio = CONTRACT["log_rate_ratio" if log else "error_rate_ratio"]
    return "supports" if abnormal[field] >= CONTRACT["min_events"] and a >= max(b + delta, b * ratio) else "not_met"


def metric_shift(normal, abnormal):
    if not normal or not abnormal or min(normal["n"], abnormal["n"]) < CONTRACT["min_samples"]:
        return "insufficient"
    b, a = normal.get("mean"), abnormal.get("mean")
    if a is None or b is None or b < 0:
        return "insufficient"
    return "supports" if a > b and a >= max(b * CONTRACT["metric_ratio"], b + 1e-9) else "not_met"
