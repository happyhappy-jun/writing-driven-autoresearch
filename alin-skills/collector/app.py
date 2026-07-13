#!/usr/bin/env python3
"""Minimal central collector for ALIN skill-usage telemetry.

Receives POSTs from the plugin hook (hooks/log_skill_usage.py) and stores them
in a SQLite DB. Run this once, somewhere the whole lab can reach (the same box
that hosts your LiteLLM proxy is a natural home), then point every member's
plugin at it:

    export ALIN_SKILL_COLLECTOR_URL=https://your-host/ingest
    export ALIN_SKILL_COLLECTOR_TOKEN=some-shared-secret   # optional

Run:
    pip install fastapi uvicorn
    ALIN_COLLECTOR_TOKEN=some-shared-secret \
      uvicorn collector.app:app --host 0.0.0.0 --port 8787

Endpoints:
    POST /ingest    store one event (JSON body from the hook)
    GET  /stats     usage aggregates (by skill / user / day)
    GET  /health    liveness
"""

import json
import os
import sqlite3
import threading

from fastapi import FastAPI, Header, HTTPException, Request

DB_PATH = os.environ.get("ALIN_COLLECTOR_DB", "alin_skill_usage.sqlite")
TOKEN = os.environ.get("ALIN_COLLECTOR_TOKEN", "").strip()

app = FastAPI(title="ALIN skill-usage collector")
_lock = threading.Lock()


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS events (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               ts TEXT, skill TEXT, trigger TEXT, event TEXT,
               user TEXT, host TEXT, session_id TEXT, cwd TEXT,
               raw TEXT
           )"""
    )
    return conn


def _check_auth(authorization):
    if TOKEN and authorization != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/ingest")
async def ingest(request: Request, authorization: str = Header(default="")):
    _check_auth(authorization)
    rec = await request.json()
    with _lock, _db() as conn:
        conn.execute(
            """INSERT INTO events
               (ts, skill, trigger, event, user, host, session_id, cwd, raw)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                rec.get("ts"), rec.get("skill"), rec.get("trigger"),
                rec.get("event"), rec.get("user"), rec.get("host"),
                rec.get("session_id"), rec.get("cwd"),
                json.dumps(rec, ensure_ascii=False),
            ),
        )
    return {"ok": True}


@app.get("/stats")
def stats(authorization: str = Header(default="")):
    _check_auth(authorization)
    with _db() as conn:
        by_skill = conn.execute(
            "SELECT skill, COUNT(*) c, COUNT(DISTINCT user) u "
            "FROM events GROUP BY skill ORDER BY c DESC"
        ).fetchall()
        by_user = conn.execute(
            "SELECT user, COUNT(*) c FROM events GROUP BY user ORDER BY c DESC"
        ).fetchall()
        by_day = conn.execute(
            "SELECT substr(ts,1,10) d, COUNT(*) c FROM events "
            "GROUP BY d ORDER BY d DESC LIMIT 30"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    return {
        "total_invocations": total,
        "by_skill": [{"skill": s, "calls": c, "distinct_users": u} for s, c, u in by_skill],
        "by_user": [{"user": u, "calls": c} for u, c in by_user],
        "by_day": [{"day": d, "calls": c} for d, c in by_day],
    }
