"""In-process task queue / scheduler. No Redis/RabbitMQ for 2 devices.

Features: async worker, retry/backoff, idempotency (dedup by key), persistence
to SQLite so a restart mid-task is recoverable.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Optional

from .events import bus
from .scenarios.engine import ScenarioEngine
from .scenarios.schema import load_scenario
from .store import store


class Scheduler:
    def __init__(self) -> None:
        # Created lazily in start() so it binds to the RUNNING loop (important for
        # TestClient / any host that runs the app on a different loop than import).
        self._queue: Optional[asyncio.Queue] = None
        self._worker: Optional[asyncio.Task] = None

    def _q(self) -> asyncio.Queue:
        if self._queue is None:
            self._queue = asyncio.Queue()
        return self._queue

    def start(self) -> None:
        self._q()
        if not self._worker:
            self._worker = asyncio.create_task(self._run())

    async def recover(self) -> None:
        """Re-queue tasks left unfinished by a previous run (crash/restart).

        Tasks restart from step 0 — idempotency at enqueue prevents duplicate
        enqueues, but true mid-step resume is a backlog item (docs/ARCHITECTURE).
        """
        for tid in await store.list_pending_task_ids():
            await self._update(tid, state="queued", message="recovered")
            await self._q().put(tid)

    async def stop(self) -> None:
        if self._worker:
            self._worker.cancel()

    async def enqueue(self, scenario: str, udid: str, params: dict[str, Any],
                      idempotency_key: str = "") -> str:
        if idempotency_key:
            existing = await store.find_task_by_idem(idempotency_key)
            if existing:
                return existing["id"]
        task_id = uuid.uuid4().hex[:12]
        sc = load_scenario(scenario)
        await store.save_task({
            "id": task_id, "scenario": scenario, "udid": udid, "state": "queued",
            "step": 0, "total_steps": sc.total_steps, "message": "queued",
            "params": params, "idempotency_key": idempotency_key or task_id,
        })
        await self._q().put(task_id)
        await bus.emit("task.updated", id=task_id, state="queued")
        return task_id

    async def _run(self) -> None:
        q = self._q()
        while True:
            task_id = await q.get()
            await self._execute(task_id)

    async def _execute(self, task_id: str) -> None:
        task = await store.get_task(task_id)
        if not task:
            return
        scenario = load_scenario(task["scenario"])
        udid = task["udid"]
        await self._update(task_id, state="running", message="running")
        # Live per-step progress is broadcast by the engine over the WS event
        # bus (task.progress); the scheduler only persists lifecycle states to
        # avoid racing writes on the same row.
        engine = ScenarioEngine(udid)
        try:
            ok = await engine.run(scenario, task.get("params", {}))
            await self._update(task_id, state="done" if ok else "failed",
                               message="done" if ok else "failed")
        except Exception as e:  # noqa: BLE001
            await self._update(task_id, state="failed", message=str(e))

    async def _update(self, task_id: str, **fields: Any) -> None:
        await store.update_task_fields(task_id, **fields)
        await bus.emit("task.updated", id=task_id, **fields)


scheduler = Scheduler()
