"""Platform detection and permission helpers."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from typing import List

import psutil


@dataclass(frozen=True)
class PlatformInfo:
    system: str
    release: str
    version: str
    machine: str
    python_version: str
    is_admin: bool
    session_type: str
    is_wayland: bool
    has_xdotool: bool
    has_ydotool: bool
    has_cliclick: bool
    has_pyautogui: bool
    has_xlib: bool

    @property
    def modifier_key(self) -> str:
        return "cmd" if self.system == "Darwin" else "ctrl"

    @property
    def window_switch_combo(self) -> tuple[str, str]:
        return ("cmd", "tab") if self.system == "Darwin" else ("alt", "tab")


class PlatformManager:
    BROWSER_PROCESS_MAP = {
        "Windows": {
            "chrome.exe": "Chrome",
            "msedge.exe": "Edge",
            "firefox.exe": "Firefox",
        },
        "Darwin": {
            "Google Chrome": "Chrome",
            "Google Chrome Helper": "Chrome",
            "Safari": "Safari",
            "firefox": "Firefox",
            "Microsoft Edge": "Edge",
        },
        "Linux": {
            "chrome": "Chrome",
            "chromium": "Chrome",
            "microsoft-edge": "Edge",
            "firefox": "Firefox",
        },
    }

    @staticmethod
    def _command_exists(name: str) -> bool:
        return shutil.which(name) is not None

    @staticmethod
    def _has_pyautogui() -> bool:
        try:
            import pyautogui  # noqa: F401

            return True
        except Exception:
            return False

    @staticmethod
    def _has_xlib() -> bool:
        try:
            from Xlib import display as _display  # noqa: F401

            return True
        except Exception:
            return False

    @staticmethod
    def _is_admin(system: str) -> bool:
        if system == "Windows":
            try:
                import ctypes

                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            except Exception:
                return False

        if hasattr(os, "geteuid"):
            try:
                return os.geteuid() == 0
            except Exception:
                return False
        return False

    @classmethod
    def detect(cls) -> PlatformInfo:
        system = platform.system()
        session_type = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()

        return PlatformInfo(
            system=system,
            release=platform.release(),
            version=platform.version(),
            machine=platform.machine(),
            python_version=platform.python_version(),
            is_admin=cls._is_admin(system),
            session_type=session_type,
            is_wayland=(system == "Linux" and session_type == "wayland"),
            has_xdotool=cls._command_exists("xdotool"),
            has_ydotool=cls._command_exists("ydotool"),
            has_cliclick=cls._command_exists("cliclick"),
            has_pyautogui=cls._has_pyautogui(),
            has_xlib=cls._has_xlib(),
        )

    @staticmethod
    def detect_running_browsers(info: PlatformInfo) -> List[str]:
        process_map = PlatformManager.BROWSER_PROCESS_MAP.get(info.system, {})
        seen: set[str] = set()

        for proc in psutil.process_iter(attrs=["name"]):
            name = (proc.info.get("name") or "").strip()
            browser = process_map.get(name)
            if browser:
                seen.add(browser)

        return sorted(seen)

    @staticmethod
    def has_macos_accessibility() -> bool:
        script = 'tell application "System Events" to get name of first process'
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def permission_instructions(info: PlatformInfo) -> list[str]:
        if info.system == "Darwin":
            return [
                "Open System Settings > Privacy & Security > Accessibility.",
                "Enable permissions for your Terminal or Python app.",
                "If keyboard events fail, also enable Input Monitoring.",
            ]

        if info.system == "Linux":
            lines = []
            if not info.has_xdotool:
                lines.append("Install xdotool for X11 fallback: sudo apt-get install xdotool")
            if info.is_wayland and not info.has_ydotool:
                lines.append("Install ydotool for Wayland fallback and start ydotoold.")
            if not lines:
                lines.append("Linux permissions look good for current session type.")
            return lines

        lines = []
        if not info.is_admin:
            lines.append("Run terminal as Administrator for more consistent key injection.")
            lines.append("If UAC prompts block input, elevate before starting automation.")
        else:
            lines.append("Administrator mode detected.")
        return lines
