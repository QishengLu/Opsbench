from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
TABLES = [f"{w}_{m}" for w in ("normal", "abnormal")
          for m in ("traces", "logs", "metrics", "metrics_sum", "metrics_histogram")]


def clean(x):
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if x is None or isinstance(x, (str, int, float, bool)):
        return x
    return str(x)


def canonical(x):
    return json.dumps(clean(x), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(x):
    return hashlib.sha256(canonical(x).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def dump(path, x):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(x), ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def quote(s):
    return "'" + str(s).replace("'", "''") + "'"


def ident(s):
    return '"' + s.replace('"', '""') + '"'


class Store:
    def __init__(self, case_dir):
        self.case_dir = Path(case_dir)
        self.con = duckdb.connect(":memory:")
        self.con.execute("SET TimeZone='UTC'")
        self.con.execute("SET threads=1")
        self.con.execute("SET memory_limit='2GB'")
        self.sources, self.queries = {}, []
        for table in TABLES:
            path = self.case_dir / "telemetry" / f"{table}.parquet"
            if not path.exists():
                self.sources[table] = {"status": "unavailable"}
                continue
            # Materialize every column: SQL replay cannot reach any external files or GT.
            self.con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_parquet({quote(path)})")
            schema = self.con.execute(f"DESCRIBE {table}").fetchall()
            self.sources[table] = {"status": "available", "path": f"telemetry/{table}.parquet",
                                   "sha256": file_hash(path), "schema": {r[0]: r[1] for r in schema}}
        self.con.execute("SET enable_external_access=false")

    def query(self, sql, purpose):
        cur = self.con.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = clean([dict(zip(columns, row)) for row in cur.fetchall()])
        qid = "q_" + digest(sql)[:20]
        if not any(q["id"] == qid for q in self.queries):
            self.queries.append({"id": qid, "purpose": purpose, "sql": sql, "rows": rows,
                                 "rows_sha256": digest(rows), "truncated": False})
        return qid, rows

    def has(self, table):
        return self.sources[table]["status"] == "available"

    def close(self):
        self.con.close()
