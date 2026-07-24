"""API request/response models."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class DeviceInfo(BaseModel):
    udid: str
    name: str
    ios: str
    status: str = "unknown"        # unknown | offline | online
    wda: str = "down"             # down | starting | ready
    tunnel: str = "down"          # down | up
    ip: Optional[str] = None
    vpn_region: Optional[str] = None
    profile_days_left: Optional[int] = None  # WDA signing profile validity
    point_w: Optional[float] = None          # logical screen size (points) for tap mapping
    point_h: Optional[float] = None


class TapRequest(BaseModel):
    x: float
    y: float


class TypeRequest(BaseModel):
    text: str


class LaunchRequest(BaseModel):
    bundle_id: str


class OpenURLRequest(BaseModel):
    url: str


class ScenarioRunRequest(BaseModel):
    udid: str
    params: dict[str, Any] = {}


class Task(BaseModel):
    id: str
    scenario: str
    udid: str
    state: str = "queued"          # queued | running | paused | done | failed
    step: int = 0
    total_steps: int = 0
    message: str = ""
    params: dict[str, Any] = {}
