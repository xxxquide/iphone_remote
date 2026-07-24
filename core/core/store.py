"""SQLite persistence (aiosqlite). Single-writer, WAL. Schema + tiny helpers.

Migrations are intentionally trivial here (CREATE TABLE IF NOT EXISTS). For
production, switch to versioned migrations (see docs/ARCHITECTURE.md).
"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

import aiosqlite

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    udid TEXT PRIMARY KEY,
    name TEXT, ios TEXT, status TEXT, wda TEXT, tunnel TEXT,
    ip TEXT, vpn_region TEXT, profile_days_left INTEGER, updated REAL
);
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY, platform TEXT, handle TEXT, udid TEXT,
    last_ip TEXT, runs_since_rotation INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY, scenario TEXT, udid TEXT, state TEXT,
    step INTEGER, total_steps INTEGER, message TEXT, params TEXT,
    idempotency_key TEXT, created REAL, updated REAL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, type TEXT, payload TEXT
);
"""


class Store:
    def __init__(self, path: str) -> None:
        self.path = path
        self.db: Optional[aiosqlite.Connection] = None

    async def open(self) -> None:
        self.db = await aiosqlite.connect(self.path)
        self.db.row_factory = aiosqlite.Row
        await self.db.execute("PRAGMA journal_mode=WAL;")
        await self.db.executescript(SCHEMA)
        await self.db.commit()

    async def close(self) -> None:
        if self.db:
            await self.db.close()

    async def upsert_device(self, d: dict[str, Any]) -> None:
        assert self.db
        d = {**d, "updated": time.time()}
        cols = ",".join(d.keys())
        ph = ",".join("?" for _ in d)
        upd = ",".join(f"{k}=excluded.{k}" for k in d if k != "udid")
        await self.db.execute(
            f"INSERT INTO devices ({cols}) VALUES ({ph}) "
            f"ON CONFLICT(udid) DO UPDATE SET {upd}",
            list(d.values()),
        )
        await self.db.commit()

    async def list_devices(self) -> list[dict]:
        assert self.db
        cur = await self.db.execute("SELECT * FROM devices ORDER BY name")
        return [dict(r) for r in await cur.fetchall()]

    async def save_task(self, t: dict[str, Any]) -> None:
        assert self.db
        t = {**t, "updated": time.time()}
        t["params"] = json.dumps(t.get("params", {}))
        t.setdefault("created", time.time())
        cols = ",".join(t.keys())
        ph = ",".join("?" for _ in t)
        upd = ",".join(f"{k}=excluded.{k}" for k in t if k != "id")
        await self.db.execute(
            f"INSERT INTO tasks ({cols}) VALUES ({ph}) "
            f"ON CONFLICT(id) DO UPDATE SET {upd}",
            list(t.values()),
        )
        await self.db.commit()

    async def update_task_fields(self, task_id: str, **fields: Any) -> None:
        """Targeted UPDATE of only the given columns — avoids read-modify-write
        clobbering (e.g. a late progress write reverting a final state)."""
        assert self.db
        if not fields:
            return
        fields["updated"] = time.time()
        if "params" in fields:
            fields["params"] = json.dumps(fields["params"])
        sets = ",".join(f"{k}=?" for k in fields)
        await self.db.execute(
            f"UPDATE tasks SET {sets} WHERE id=?", [*fields.values(), task_id]
        )
        await self.db.commit()

    async def get_task(self, task_id: str) -> Optional[dict]:
        assert self.db
        cur = await self.db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        row = await cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["params"] = json.loads(d.get("params") or "{}")
        return d

    async def list_pending_task_ids(self) -> list[str]:
        assert self.db
        cur = await self.db.execute(
            "SELECT id FROM tasks WHERE state IN ('queued','running') ORDER BY created")
        return [r["id"] for r in await cur.fetchall()]

    async def find_task_by_idem(self, key: str) -> Optional[dict]:
        assert self.db
        cur = await self.db.execute(
            "SELECT * FROM tasks WHERE idempotency_key=? AND state IN ('queued','running','done')",
            (key,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def log_event(self, type_: str, payload: dict) -> None:
        assert self.db
        await self.db.execute(
            "INSERT INTO events (ts,type,payload) VALUES (?,?,?)",
            (time.time(), type_, json.dumps(payload)),
        )
        await self.db.commit()


store = Store(settings.db_path)
