"""Human-readable case review and literal-indexed DIMACS CNF."""
from collections import Counter

from .storage import dump


def write_review(root, cnf):
    case=cnf['case']
    literals={c['id']:c for c in cnf['literals']}
    indices={lid:i+1 for i,lid in enumerate(sorted(literals))}
    lines=[f"c OpsBench V2 {case}","c Empty clause = unresolved reference obligation; retained deliberately.",
           f"p cnf {len(indices)} {len(cnf['clauses'])}"]
    for clause in cnf['clauses']:
        lines.append('c '+clause['id'])
        lines.append(' '.join([str(indices[lid]) for lid in clause['literals']]+['0']))
    (root/'phi'/f'{case}.cnf').write_text('\n'.join(lines)+'\n')
    dump(root/'phi'/f'{case}.variables.json',{str(v):k for k,v in indices.items()})
    lines=[f'# {case}', '',f"状态：{cnf['status']}；{cnf['summary']['covered']}/{cnf['summary']['n_clauses']} 条义务有规则证据。",'',
           '这些是离线参考标注。传播支持表示请求级关联，不证明因果。所有未覆盖义务保留。','',
           '| 义务 | 含义 | 状态 | 规则及证据数 |','|---|---|---|---|']
    for c in cnf['clauses']:
        counts=Counter(literals[lid]['rule_id'] for lid in c['literals'])
        lines.append(f"| {c['id']} | {c['kind']} | {c['status']} | "+(', '.join(f'{k}: {v}' for k,v in sorted(counts.items())) or '证据不足')+' |')
    lines+=['','原始数据、完整 SQL 及全部候选在 `data/cases/` 和 `evidence/` 中；本表按规则归并展示，CNF 中不裁剪替代证据。','']
    out=root/'reports/cases'/f'{case}.md'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text('\n'.join(lines))
