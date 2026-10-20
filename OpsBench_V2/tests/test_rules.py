from opsbench_v2.rules import increased_latency, increased_rate, metric_shift
from opsbench_v2.enumerate import make_obligations


def test_missing_and_small_samples_are_not_refutations():
    assert increased_latency(None,{"n":100,"median_ms":500})=="insufficient"
    assert increased_rate({"n":0,"errors":0},{"n":10,"errors":10})=="insufficient"
    assert increased_latency({"n":4,"median_ms":1},{"n":10,"median_ms":100})=="insufficient"


def test_latency_requires_relative_and_absolute_increase():
    assert increased_latency({"n":10,"median_ms":1},{"n":10,"median_ms":4})=="not_met"
    assert increased_latency({"n":10,"median_ms":100},{"n":10,"median_ms":130})=="not_met"
    assert increased_latency({"n":10,"median_ms":10},{"n":10,"median_ms":100})=="supports"


def test_rates_not_raw_counts():
    assert increased_rate({"n":100,"errors":10},{"n":1000,"errors":100})=="not_met"
    assert increased_rate({"n":100,"errors":0},{"n":100,"errors":10})=="supports"
    assert metric_shift(None,{"n":100,"mean":999})=="insufficient"


def test_boundary_does_not_mean_local_anomaly():
    gt={"nodes":[{"component":"service|a"},{"component":"service|b"}],
        "edges":[{"source":"service|a","target":"service|b"}],
        "root_causes":[{"component":"service|a"},{"component":"service|b"}]}
    _,_,_,obs=make_obligations(gt)
    assert {o['kind'] for o in obs if o['id'].startswith('node:')}=={'node_involvement'}
    assert next(o for o in obs if o['kind']=='dependency')['subject']['caller']=='b'
