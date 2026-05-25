"""Main automation controller for cross-platform WFH assistant."""

from __future__ import annotations

import subprocess
from typing import Callable

from modules.activity_logger import ActivityLogger
from modules.input_backends import CrossPlatformInput
from modules.platform_manager import PlatformManager
from modules.simulation_engines import (
    BrowserEngine,
    EngineContext,
    KeyboardEngine,
    MouseEngine,
    SPEED_PROFILES,
    VSCodeEngine,
)


class WFHController:
    def __init__(self, logger: ActivityLogger | None = None) -> None:
        self.logger = logger or ActivityLogger(log_file="wfh.log")
        self.info = PlatformManager.detect()
        self.input_driver = CrossPlatformInput(self.info, self.logger)

        self._speed = "Medium"
        self.running = False

        ctx = EngineContext(
            info=self.info,
            input_driver=self.input_driver,
            logger=self.logger,
            get_speed=self.get_speed,
        )
        self.mouse = MouseEngine(ctx)
        self.keyboard = KeyboardEngine(ctx)
        self.browser = BrowserEngine(ctx, detect_browsers=self.detect_running_browsers)
        self.vscode = VSCodeEngine(ctx)

    def get_speed(self) -> str:
        return self._speed

    def set_speed(self, speed: str) -> None:
        if speed not in SPEED_PROFILES:
            raise ValueError(f"Unsupported speed profile: {speed}")
        self._speed = speed
        self.logger.log("SYSTEM", f"speed set to {speed}")

    def detect_running_browsers(self) -> list[str]:
        return PlatformManager.detect_running_browsers(self.info)

    def start(self) -> None:
        if self.running:
            return

        self.running = True
        self.logger.log("SYSTEM", "starting automation")
        self.mouse.start()
        self.keyboard.start()
        self.browser.start()
        self.vscode.start()
        self.logger.log("SYSTEM", "automation running")

    def stop(self) -> None:
        if not self.running:
            return

        self.running = False
        self.mouse.stop()
        self.keyboard.stop()
        self.browser.stop()
        self.vscode.stop()
        self.logger.log("SYSTEM", "automation stopped")

    def permission_report(self) -> list[str]:
        report: list[str] = []
        info = self.info

        report.append(f"Detected OS: {info.system} {info.release}")
        report.append(f"CPU: {info.machine}")
        report.append(f"Python: {info.python_version}")

        if info.system == "Darwin":
            has_accessibility = PlatformManager.has_macos_accessibility()
            report.append(f"Accessibility permission: {'granted' if has_accessibility else 'not granted'}")
            report.extend(PlatformManager.permission_instructions(info))
            report.append(
                "Fallbacks: AppleScript for keyboard, cliclick for mouse when pyautogui fails."
            )

        elif info.system == "Linux":
            report.append(f"Session: {info.session_type or 'unknown'}")
            report.append(f"xdotool available: {'yes' if info.has_xdotool else 'no'}")
            report.append(f"ydotool available: {'yes' if info.has_ydotool else 'no'}")
            report.append(f"python3-xlib available: {'yes' if info.has_xlib else 'no'}")
            report.extend(PlatformManager.permission_instructions(info))

        else:
            report.append(f"Administrator mode: {'yes' if info.is_admin else 'no'}")
            report.extend(PlatformManager.permission_instructions(info))
            report.append("UAC note: if prompts appear, relaunch app as Administrator.")

        report.append(f"Input backends in priority order: {self.input_driver.backend_summary()}")
        return report

    def open_macos_accessibility_settings(self) -> None:
        if self.info.system != "Darwin":
            return
        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            ],
            check=False,
        )

    def open_linux_install_hint(self) -> str:
        return "sudo apt-get install xdotool"

    def status_snapshot(self) -> dict[str, str]:
        return {
            "running": str(self.running),
            "speed": self._speed,
            "platform": f"{self.info.system} {self.info.release}",
            "modifier": self.info.modifier_key,
        }
