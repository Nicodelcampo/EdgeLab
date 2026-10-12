"""Libro de corridas (SQLite, solo agregar estados): telemetría para optimizar y resultados para aprender. Un spec_hash no se lanza dos veces."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

SCHEMA = """CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY, spec_hash TEXT UNIQUE, family TEXT, grp TEXT, kind TEXT, spec TEXT, status TEXT,
 launched_at REAL, finished_at REAL, seconds REAL, handle TEXT, failure TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, event TEXT, detail TEXT);"""


class RunLedger:
    def __init__(self, path: Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True); self.db = sqlite3.connect(str(path)); self.db.executescript(SCHEMA)

    def seen(self, spec_hash: str) -> bool:
        return self.db.execute("SELECT 1 FROM runs WHERE spec_hash=?", (spec_hash,)).fetchone() is not None

    def add(self, spec, handle: str) -> None:
        self.db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (spec.run_id, spec.spec_hash(), spec.family, spec.group, spec.kind,
                        json.dumps(spec.__dict__, default=list), "RUNNING", time.time(), None, None, handle, None, None))
        self.event(spec.run_id, "launched", handle); self.db.commit()

    def event(self, run_id, event, detail=""):
        self.db.execute("INSERT INTO events(run_id,ts,event,detail) VALUES(?,?,?,?)", (run_id, time.time(), event, str(detail))); self.db.commit()

    def finish(self, run_id, status, result=None, failure=None):
        r = self.db.execute("SELECT launched_at FROM runs WHERE run_id=?", (run_id,)).fetchone(); now = time.time()
        self.db.execute("UPDATE runs SET status=?, finished_at=?, seconds=?, result=?, failure=? WHERE run_id=?",
                        (status, now, now - r[0], json.dumps(result) if result is not None else None, failure, run_id)); self.event(run_id, status, failure or ""); self.db.commit()

    def running(self):
        return [dict(zip(("run_id", "handle", "launched_at"), x)) for x in self.db.execute("SELECT run_id,handle,launched_at FROM runs WHERE status='RUNNING'")]

    def launched_since(self, t: float) -> int:
        return self.db.execute("SELECT COUNT(*) FROM runs WHERE launched_at>=?", (t,)).fetchone()[0]

    def outcomes(self):
        """(family, group, hit) de las corridas ya analizadas: alimenta al selector."""
        out = []
        for fam, grp, res in self.db.execute("SELECT family,grp,result FROM runs WHERE status='ANALYZED'"):
            out.append((fam, grp, bool(json.loads(res).get("hit"))))
        return out

    def telemetry(self, kind=None):
        q = "SELECT family,grp,kind,seconds,status,failure,spec FROM runs WHERE status IN ('ANALYZED','FAILED')"
        return [dict(zip(("family", "group", "kind", "seconds", "status", "failure", "spec"), x)) for x in self.db.execute(q)]
