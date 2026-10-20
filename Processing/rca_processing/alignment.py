"""Offline path association. Candidate association is NOT validated entailment."""
from __future__ import annotations

from .common import subject_services


def component(value):
    if not value.startswith("service|"):
        raise ValueError("Corrected service-level GT required")
    return value.split("|", 1)[1]


def obligations(graph):
    nodes = sorted({component(n["component"]) for n in graph["nodes"]})
    edges = sorted({(component(e["source"]), component(e["target"])) for e in graph["edges"]})
    roots = {component(r["component"]) for r in graph["root_causes"]}
    if not roots <= set(nodes) or any(a not in nodes or b not in nodes for a, b in edges):
        raise ValueError("Annotation graph has dangling components")
    boundary = roots if len(roots) == 2 and any({a, b} == roots for a, b in edges) else set()
    clauses = [{"id": f"node:{n}", "kind": "node", "service": n} for n in nodes]
    for source, target in edges:
        for kind in ("dependency", "propagation"):
            clauses.append({"id": f"{kind}:{source}->{target}", "kind": kind,
                            "caller": target, "callee": source})
    if boundary:
        clauses.append({"id": "root_boundary", "kind": "boundary", "ends": sorted(boundary)})
    return clauses


def linked_calls(record):
    if record["modality"] != "trace":
        return set()
    calls = set()
    subject = record["subject"]
    if record["kind"] == "three_hop_path":
        path = subject["path"]
        calls.update(zip(path, path[1:]))
    elif record["kind"] == "high_latency_window":
        callee = subject.get("service_name")
        calls.update((e["caller"], callee) for e in record["observation"]["events"] if e["caller"])
    return calls


def align(records, graph, reviews=None):
    reviews = reviews or {}
    selected = {r["id"]: r for r in records if r["selected"]}
    clauses = []
    for obligation in obligations(graph):
        associated = []
        for eid, record in selected.items():
            kind = obligation["kind"]
            if kind == "node":
                match = obligation["service"] in subject_services(record["subject"])
            elif kind in ("dependency", "propagation"):
                match = (obligation["caller"], obligation["callee"]) in linked_calls(record)
            else:
                ends = set(obligation["ends"])
                match = any({a, b} == ends for a, b in linked_calls(record))
            if match:
                associated.append(eid)
        accepted = []
        for eid, decision in reviews.get(obligation["id"], {}).items():
            if eid not in selected:
                raise ValueError(f"Review references unselected/unknown evidence: {eid}")
            if decision not in ("supports", "refutes", "unresolved"):
                raise ValueError("Invalid review verdict")
            if decision == "supports":
                accepted.append(eid)
        clauses.append({**obligation, "candidate_ids": sorted(associated),
                        "literals": sorted(accepted),
                        "status": "covered" if accepted else "open"})
    known = {c["id"] for c in clauses}
    if set(reviews) - known:
        raise ValueError("Review references unknown obligations")
    return {
        "privileged_offline_artifact": True,
        "semantics": "Candidates associated by entity/exact span path. Only reviewed supports "
                     "enter CNF. Statistical anomalies and path membership do not prove propagation.",
        "clauses": clauses,
        "summary": {"obligations": len(clauses),
                    "candidate_associated": sum(bool(c["candidate_ids"]) for c in clauses),
                    "covered": sum(bool(c["literals"]) for c in clauses),
                    "open": sum(not c["literals"] for c in clauses)},
    }


def dimacs(phi):
    ids = sorted({eid for c in phi["clauses"] for eid in c["literals"]})
    mapping = {eid: i + 1 for i, eid in enumerate(ids)}
    lines = [f"p cnf {len(ids)} {len(phi['clauses'])}"]
    lines += [" ".join([*(str(mapping[e]) for e in c["literals"]), "0"])
              for c in phi["clauses"]]
    return "\n".join(lines) + "\n", mapping
