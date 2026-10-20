"""Replay all SQL, check source hashes, and rebuild complete deterministic artifacts."""
from __future__ import annotations

import argparse
import json
import platform

import duckdb
import yaml

from .enumerate import Enumerator
from .prepare_cases import load_case_list
from .storage import ROOT, canonical, digest, dump, file_hash


def verify_case(case_id, root=ROOT):
    folder=root/"evidence"/case_id
    manifest=json.loads((folder/"manifest.json").read_text())
    queries=json.loads((folder/"queries.json").read_text())
    candidates=[json.loads(line) for line in (folder/"candidates.jsonl").read_text().splitlines()]
    cnf=yaml.safe_load((root/"phi"/f"{case_id}.yaml").read_text())
    e=Enumerator(root/"data/cases"/case_id)
    try:
        assert file_hash(e.case_dir/"ground_truth/gt.json")==manifest["gt_sha256"], "GT changed"
        assert e.store.sources==manifest["sources"], "Telemetry changed"
        for q in queries:
            _,rows=e.store.query(q["sql"],"replay")
            assert digest(rows)==q["rows_sha256"]==digest(q["rows"]), f"SQL mismatch {q['id']}"
        e.store.queries.clear()
        new_cnf,new_evidence=e.build()
        assert canonical(new_cnf)==canonical(cnf), "CNF rebuild mismatch"
        assert canonical(new_evidence["candidates"])==canonical(candidates), "Candidate rebuild mismatch"
        assert canonical(new_evidence["manifest"])==canonical(manifest), "Manifest/code changed"
        assert canonical(new_evidence["queries"])==canonical(queries), "Query completeness mismatch"
        lookup={c["id"]:c for c in candidates}
        qids={q["id"] for q in queries}
        for c in cnf["clauses"]:
            assert not c["excluded_from_denominator"]
            assert (c["status"]=="covered")==bool(c["literals"])
            for lid in c["literals"]:
                literal=lookup[lid]
                assert literal["verdict"]=="supports" and c["id"] in literal["obligation_ids"]
                assert literal["query_refs"] and set(literal["query_refs"])<=qids
        return {"case":case_id,"passed":True,"sql_replayed":len(queries),
                "candidate_rebuild_count":len(candidates),"cnf_rebuild_identical":True,
                "cnf_sha256":file_hash(root/"phi"/f"{case_id}.yaml")}
    finally:
        e.store.close()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cases",nargs="+",default=[str(ROOT/"data/index/pilot10.txt")])
    args=p.parse_args()
    results=[]
    for case in load_case_list(args.cases):
        r=verify_case(case)
        results.append(r)
        print(json.dumps(r),flush=True)
    dump(ROOT/"reports/verification.json",{"python":platform.python_version(),"duckdb":duckdb.__version__,"cases":results})


if __name__=="__main__": main()
