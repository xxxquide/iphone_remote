"""Secrets via the macOS login Keychain (`security` CLI). No plaintext on disk.

Used for social-account credentials, the WDA .p12 password, API tokens, etc.
On non-macOS hosts (e.g. CI/sandbox) the calls raise NotAvailable; callers should
degrade gracefully. Argv construction is factored out so it can be unit-tested
without a real Keychain.
"""
from __future__ import annotations

import platform
import subprocess

SERVICE_PREFIX = "com.orchestrator"


class NotAvailable(RuntimeError):
    pass


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def _add_argv(service: str, account: str, secret: str) -> list[str]:
    return ["security", "add-generic-password", "-U",
            "-s", f"{SERVICE_PREFIX}.{service}", "-a", account, "-w", secret]


def _get_argv(service: str, account: str) -> list[str]:
    return ["security", "find-generic-password",
            "-s", f"{SERVICE_PREFIX}.{service}", "-a", account, "-w"]


def _del_argv(service: str, account: str) -> list[str]:
    return ["security", "delete-generic-password",
            "-s", f"{SERVICE_PREFIX}.{service}", "-a", account]


def set_secret(service: str, account: str, secret: str) -> None:
    if not _is_macos():
        raise NotAvailable("Keychain only available on macOS")
    subprocess.run(_add_argv(service, account, secret), check=True,
                   capture_output=True)


def get_secret(service: str, account: str) -> str | None:
    if not _is_macos():
        raise NotAvailable("Keychain only available on macOS")
    res = subprocess.run(_get_argv(service, account), capture_output=True, text=True)
    return res.stdout.strip() if res.returncode == 0 else None


def delete_secret(service: str, account: str) -> bool:
    if not _is_macos():
        raise NotAvailable("Keychain only available on macOS")
    return subprocess.run(_del_argv(service, account),
                          capture_output=True).returncode == 0


# Shared API token so the native app and the core agree without hardcoding.
API_SERVICE = "api"
API_ACCOUNT = "token"


def store_api_token(token: str) -> None:
    """Persist the core's API token to the Keychain (best-effort, macOS only)."""
    set_secret(API_SERVICE, API_ACCOUNT, token)


def get_api_token() -> str | None:
    return get_secret(API_SERVICE, API_ACCOUNT)
