import asyncio

from core.scenarios.engine import plan_steps
from core.scenarios.schema import Step


def test_plan_steps_fresh_returns_all():
    steps = [Step(action="a"), Step(action="b"), Step(action="c")]
    assert plan_steps(steps, 0) == list(enumerate(steps))


def test_plan_steps_resume_reruns_always_then_rest():
    steps = [
        Step(action="ensure_vpn", always=True),   # 0
        Step(action="put_media"),                 # 1
        Step(action="launch", always=True),       # 2
        Step(action="tap"),                       # 3
        Step(action="post"),                      # 4
    ]
    plan = plan_steps(steps, start_step=3)
    assert [i for i, _ in plan] == [0, 2, 3, 4]   # always setup (0,2) re-run, then 3,4


def test_resume_completes_from_persisted_step(tmp_path, monkeypatch):
    """A task 'crashed' mid-scenario resumes and finishes (mock).

    Hermetic: uses its own Store (fresh DB) injected into the scheduler module,
    and closes it in finally so no aiosqlite thread lingers between tests.
    """
    from core.store import Store
    import core.scheduler as sched_mod

    fresh = Store(str(tmp_path / "resume.db"))
    monkeypatch.setattr(sched_mod, "store", fresh)   # scheduler + _execute use this store

    async def main():
        await fresh.open()
        sched = sched_mod.Scheduler()
        sched.start()
        try:
            await fresh.save_task({
                "id": "resume-xyz", "scenario": "tiktok_upload", "udid": "MOCK-15PM-0001",
                "state": "running", "step": 8, "total_steps": 13, "message": "crash",
                "params": {}, "idempotency_key": "resume-xyz",
            })
            await sched.recover()
            task = None
            for _ in range(100):
                task = await fresh.get_task("resume-xyz")
                if task and task["state"] in ("done", "failed"):
                    break
                await asyncio.sleep(0.03)
            return task
        finally:
            await sched.stop()
            await asyncio.sleep(0)
            await fresh.close()

    task = asyncio.run(main())
    assert task["state"] == "done"
    assert task["step"] == 13          # advanced to the end
