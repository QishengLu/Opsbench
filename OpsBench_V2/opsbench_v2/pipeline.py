from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import yaml

from .enumerate import Enumerator
from .render import write_review
from .prepare_cases import load_case_list
from .storage import ROOT, dump, file_hash


def run_case(case_id, root=ROOT):
    e = Enumerator(root/"data/cases"/case_id)
    try:
        cnf,evidence = e.build()
    finally:
        e.store.close()
    folder = root/"evidence"/case_id
    dump(folder/"manifest.json",evidence["manifest"])
    dump(folder/"queries.json",evidence["queries"])
    # Streaming-friendly candidate ledger; normal/context/not_met observations retained.
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"candidates.jsonl").write_text("".join(json.dumps(c,ensure_ascii=False,allow_nan=False)+"\n" for c in evidence["candidates"]))
    out = root/"phi"/f"{case_id}.yaml"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(yaml.safe_dump(cnf,sort_keys=False,allow_unicode=True,width=120))
    write_review(root, cnf)
    verdicts = Counter(c["verdict"] for c in evidence["candidates"])
    return {"case":case_id,**cnf["summary"],"candidate_verdicts":dict(verdicts),"cnf_sha256":file_hash(out),
            "open_obligations":[{"id":c["id"],"kind":c["kind"]} for c in cnf["clauses"] if c["status"]=="open"]}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cases",nargs="+",default=[str(ROOT/"data/index/pilot10.txt")])
    args=p.parse_args()
    rows=[]
    for c in load_case_list(args.cases):
        row=run_case(c)
        rows.append(row)
        print(json.dumps(row,ensure_ascii=False),flush=True)
    dump(ROOT/"reports/summary.json",rows)
    lines=["# V2 规则枚举：10-case pilot" if len(rows)==10 else "# V2 规则枚举结果", "",
           "全程无 LLM。覆盖率保留全部义务；未通过规则不等于无故障。传播子句只表示请求级关联支持，不是因果证明。", "",
           "| Case | 候选 | CNF literals | Covered / 全部 | Open |", "|---|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['case']} | {r['n_candidates']} | {r['n_literals']} | {r['covered']} / {r['n_clauses']} | {r['open']} |")
    lines += ["", "## 未覆盖义务", ""]
    for r in rows:
        lines.append(f"- **{r['case']}**: "+(", ".join(x['id'] for x in r['open_obligations']) or "无"))
    (ROOT/"reports/pilot10.md").write_text("\n".join(lines)+"\n")


if __name__=="__main__": main()
