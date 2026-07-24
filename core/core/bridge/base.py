"""Process helpers: one-shot commands and supervised long-running processes."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class CmdResult:
    rc: int
    out: str
    err: str

    @property
    def ok(self) -> bool:
        return self.rc == 0


async def run_cmd(argv: list[str], timeout: float = 60.0) -> CmdResult:
    """Run a command, capture stdout/stderr, enforce a timeout."""
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return CmdResult(124, "", f"timeout after {timeout}s: {' '.join(argv)}")
    return CmdResult(proc.returncode or 0, out.decode(errors="replace"),
                     err.decode(errors="replace"))


@dataclass
class Supervised:
    name: str
    argv: list[str]
    proc: asyncio.subprocess.Process | None = None


class ProcessSupervisor:
    """Tracks long-running child processes (tunnels, WDA runners, streams)."""

    def __init__(self) -> None:
        self._procs: dict[str, Supervised] = {}

    async def start(self, name: str, argv: list[str]) -> Supervised:
        await self.stop(name)
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        s = Supervised(name=name, argv=argv, proc=proc)
        self._procs[name] = s
        return s

    async def stop(self, name: str) -> None:
        s = self._procs.pop(name, None)
        if s and s.proc and s.proc.returncode is None:
            s.proc.terminate()
            try:
                await asyncio.wait_for(s.proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                s.proc.kill()

    def is_running(self, name: str) -> bool:
        s = self._procs.get(name)
        return bool(s and s.proc and s.proc.returncode is None)

    async def stop_all(self) -> None:
        for name in list(self._procs):
            await self.stop(name)


supervisor = ProcessSupervisor()
