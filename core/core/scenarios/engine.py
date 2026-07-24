"""Scenario engine — execute declarative steps, auto or manual.

Each step: resolve target (vision cascade) -> act (via bridge) -> post-check.
On failure: retry, then either fail the task or hand off to manual step-in.
Emits granular events so both UIs can render live progress.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from ..bridge import devicectl
from ..bridge.wda import WDAClient, client_for
from ..config import settings
from ..events import bus
from ..vision.targeting import Targeter, TargetSpec
from .. import photos, vpn
from .schema import Scenario, Step

ACTIONS = {
    "ensure_vpn", "put_media", "wake", "launch", "tap", "type",
    "open_url", "wait", "verify", "manual",
}


class PausedForManual(Exception):
    pass


class ScenarioEngine:
    def __init__(self, udid: str, on_progress: Optional[Callable] = None) -> None:
        self.udid = udid
        self.wda: WDAClient = client_for(udid)
        dev = next((d for d in settings.devices if d.udid == udid), None)
        self.targeter = Targeter(
            self.wda, udid,
            scale=dev.scale if dev else 3.0,
            screenshotter=devicectl.capture_screenshot,
        )
        self.on_progress = on_progress

    async def run(self, scenario: Scenario, params: dict[str, Any]) -> bool:
        for i, step in enumerate(scenario.steps):
            await self._progress(i, scenario.total_steps, f"{step.action}: {step.name}")
            ok = await self._run_step(step, params)
            if not ok and not step.optional:
                await self._progress(i, scenario.total_steps,
                                     f"FAILED at step {i}: {step.name}", failed=True)
                return False
        await self._progress(scenario.total_steps, scenario.total_steps, "done")
        return True

    async def _run_step(self, step: Step, params: dict[str, Any]) -> bool:
        for attempt in range(step.retries + 1):
            # Re-capture the screen for OCR/template lookups on each attempt.
            self.targeter.invalidate()
            try:
                if step.manual:
                    await bus.emit("task.manual", udid=self.udid, step=step.name)
                    # In a full build the UI resumes the task; here we log intent.
                    return True
                await self._dispatch(step, params)
                if step.verify:
                    return await self._check(step.verify)
                return True
            except Exception as e:  # noqa: BLE001 - surface + retry
                await bus.emit("task.error", udid=self.udid, step=step.name, error=str(e))
                await asyncio.sleep(0.5 * (attempt + 1))
        return False

    async def _dispatch(self, step: Step, params: dict[str, Any]) -> None:
        a = step.action
        if a == "ensure_vpn":
            dev = next(d for d in settings.devices if d.udid == self.udid)
            st = await vpn.verify_ip(self.udid, dev.vpn_expected_region)
            if not st.connected:
                raise RuntimeError("VPN not connected / IP unverified")
        elif a == "put_media":
            media = _fmt(step.value, params) if step.value else params.get("media_path", "")
            await bus.emit("task.note", udid=self.udid, note=f"put_media: {media}")
            if not await photos.put_media(self.udid, media):
                raise RuntimeError(f"put_media failed for {media}")
        elif a == "wake":
            await devicectl.open_url(self.udid, "https://localhost/")  # nudge awake
        elif a == "launch":
            await self.wda.activate_app(step.value or "")
        elif a == "tap":
            hit = await self.targeter.find(_spec(step.target))
            if not hit:
                raise RuntimeError(f"target not found: {step.target}")
            await self.wda.tap(hit.x, hit.y)
        elif a == "type":
            text = _fmt(step.value, params)
            await self.wda.type_text(text)
        elif a == "open_url":
            await devicectl.open_url(self.udid, _fmt(step.value, params))
        elif a == "wait":
            await asyncio.sleep(float(step.value or 1000) / 1000.0)
        elif a == "verify":
            if not await self._check(step.target):
                raise RuntimeError("verify failed")
        else:
            raise ValueError(f"unknown action: {a}")

    async def _check(self, target: dict[str, Any]) -> bool:
        if settings.mock_mode:
            return True
        hit = await self.targeter.find(_spec(target))
        return hit is not None

    async def _progress(self, step: int, total: int, msg: str, failed: bool = False) -> None:
        await bus.emit("task.progress", udid=self.udid, step=step, total=total,
                       message=msg, failed=failed)
        if self.on_progress:
            self.on_progress(step, total, msg, failed)


def _spec(target: dict[str, Any]) -> TargetSpec:
    xy = target.get("xy")
    return TargetSpec(
        ax_label=target.get("ax_label"),
        text=target.get("text"),
        template=target.get("template"),
        xy=tuple(xy) if xy else None,
        describe=target.get("describe"),
    )


def _fmt(value: Any, params: dict[str, Any]) -> str:
    try:
        return str(value).format(**params)
    except Exception:
        return str(value)
