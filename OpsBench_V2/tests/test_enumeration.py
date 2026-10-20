import json
from pathlib import Path

import duckdb
import pytest

from opsbench_v2.enumerate import Enumerator
from opsbench_v2.storage import quote, canonical

TRACE_SCHEMA='''time TIMESTAMPTZ,trace_id VARCHAR,span_id VARCHAR,parent_span_id VARCHAR,
span_name VARCHAR,"attr.span_kind" VARCHAR,service_name VARCHAR,duration UBIGINT,
"attr.status_code" VARCHAR,"attr.http.response.status_code" INTEGER,
"attr.http.request.method" VARCHAR,"attr.k8s.pod.name" VARCHAR'''
LOG_SCHEMA='''time TIMESTAMPTZ,trace_id VARCHAR,span_id VARCHAR,level VARCHAR,service_name VARCHAR,message VARCHAR'''


def trace(tid,sid,parent,svc,kind='Client',ms=10,error=False,operation='GET'):
    return ['2026-01-01 00:00:00+00',tid,sid,parent,operation,kind,svc,int(ms*1e6),
            'Error' if error else 'Unset',500 if error else 200,'GET','pod']


@pytest.fixture
def case_factory(tmp_path):
    def create(normal,abnormal,logs=(),edges=(('b','a'),),nodes=('a','b')):
        p=tmp_path/'case'; (p/'telemetry').mkdir(parents=True,exist_ok=True); (p/'ground_truth').mkdir(exist_ok=True)
        gt={'nodes':[{'component':'service|'+n} for n in nodes],
            'edges':[{'source':'service|'+a,'target':'service|'+b} for a,b in edges],
            'root_causes':[{'component':'service|b'}]}
        (p/'ground_truth/gt.json').write_text(json.dumps(gt))
        con=duckdb.connect()
        for w,rows in [('normal',normal),('abnormal',abnormal)]:
            con.execute(f'CREATE TABLE {w}_traces ({TRACE_SCHEMA})')
            if rows: con.executemany(f'INSERT INTO {w}_traces VALUES ({",".join("?" for _ in rows[0])})',rows)
            con.execute(f'CREATE TABLE {w}_logs ({LOG_SCHEMA})')
            if w=='abnormal' and logs: con.executemany(f'INSERT INTO {w}_logs VALUES (?,?,?,?,?,?)',logs)
            for mod in ['traces','logs']:
                con.execute(f'COPY {w}_{mod} TO {quote(p/"telemetry"/f"{w}_{mod}.parquet")} (FORMAT PARQUET)')
        con.close()
        return p
    return create


def test_trace_id_collision_does_not_create_dependency(case_factory):
    rows=[trace('t1','parent','root','a'),trace('t2','child','parent','b','Server')]
    e=Enumerator(case_factory(rows,rows))
    try:
        cnf,_=e.build()
        dep=next(c for c in cnf['clauses'] if c['kind']=='dependency')
        assert dep['status']=='open' and dep['literals']==[]
        assert cnf['summary']['n_clauses']==4
        assert all(not c['excluded_from_denominator'] for c in cnf['clauses'])
    finally: e.store.close()


def test_internal_ancestor_and_gateway_supported(case_factory):
    windows=[]
    for abnormal in [False,True]:
        rows=[]
        for i in range(10):
            rows += [trace(str(i),'s','','a','Server',100 if abnormal else 10,abnormal),
                     trace(str(i),'i','s','a','Internal',100 if abnormal else 10,abnormal),
                     trace(str(i),'p','i','a','Client',90 if abnormal else 5,abnormal),
                     trace(str(i),'c','p','b','Server',80 if abnormal else 4,abnormal)]
        windows.append(rows)
    e=Enumerator(case_factory(*windows))
    try:
        cnf,data=e.build()
        assert any(c['rule_id']=='edge_linked_error_increase' and c['verdict']=='supports' for c in data['candidates'])
        assert any(c['rule_id']=='edge_nested_latency' and c['verdict']=='supports' for c in data['candidates'])
        # Deterministic complete candidate and CNF rebuild.
        e2=Enumerator(e.case_dir)
        try: assert canonical(e2.build()[0])==canonical(cnf)
        finally: e2.store.close()
    finally: e.store.close()


def test_gateway_server_to_server(case_factory):
    rows=[trace('t','p','','a','Server'),trace('t','c','p','b','Server')]
    e=Enumerator(case_factory(rows,rows))
    try:
        _,data=e.build()
        assert any(c['rule_id']=='server_parent_dependency' and c['verdict']=='supports' for c in data['candidates'])
    finally: e.store.close()


@pytest.mark.parametrize('host,log_span,expected', [('b','p',True),('b-other','p',False),('b','other',False)])
def test_orphan_bound_only_to_unique_exact_host_and_span(case_factory,host,log_span,expected):
    rows=[trace(str(i),'p','','a',ms=100,error=True) for i in range(3)]
    logs=[['2026-01-01 00:00:00+00',str(i),log_span,'ERROR','a',f'GET http://{host}:8080/api failed'] for i in range(3)]
    e=Enumerator(case_factory([],rows,logs,edges=(('b','a'),('c','a')),nodes=('a','b','c')))
    try:
        _,data=e.build()
        found=[c for c in data['candidates'] if c['rule_id']=='url_bound_failed_call' and c['verdict']=='supports']
        assert bool(found)==expected
        assert all(c['subject']['callee']=='b' for c in found)
    finally: e.store.close()


def test_ambiguous_url_is_not_bound(case_factory):
    rows=[trace('t','p','','a',error=True)]
    logs=[['2026-01-01 00:00:00+00','t','p','ERROR','a','http://b:80/foo http://c:80/bar failed']]
    e=Enumerator(case_factory([],rows,logs))
    try:
        _,data=e.build()
        assert not any(c['rule_id']=='url_bound_dependency' for c in data['candidates'])
    finally: e.store.close()


def test_duplicate_span_identity_fails_closed(case_factory):
    row=trace('same','same','','a')
    e=Enumerator(case_factory([row,row],[]))
    try:
        with pytest.raises(ValueError,match='nonunique'):
            e.build()
    finally: e.store.close()


def test_missing_modalities_and_gt_state_do_not_fabricate_support(case_factory):
    p=case_factory([],[])
    e=Enumerator(p)
    try:
        cnf,data=e.build()
        assert cnf['summary']['covered']==0
        assert data['manifest']['inventory']['normal_metrics']['status']=='modality_unavailable'
    finally: e.store.close()
    gt=json.loads((p/'ground_truth/gt.json').read_text())
    for n in gt['nodes']: n['state']=['erroring','slow']
    (p/'ground_truth/gt.json').write_text(json.dumps(gt))
    e=Enumerator(p)
    try:
        other,other_data=e.build()
        assert other['clauses']==cnf['clauses']
        assert other_data['candidates']==data['candidates']
    finally: e.store.close()
