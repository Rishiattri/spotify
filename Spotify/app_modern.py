"""Modern HTML/CSS frontend launcher backed by the existing WFHController.

Requires:  pip install pywebview

Run:
    python app_modern.py

This keeps the legacy Tkinter UI (wfh_cross_platform.py) intact — both
frontends share the same backend modules in `modules/`.
"""

from __future__ import annotations

import os
import sys
import time
import webbrowser
from pathlib import Path

try:
    import webview
except ImportError:
    sys.stderr.write(
        "\n[!] pywebview is not installed.\n"
        "    Install it with:  pip install pywebview\n"
        "    (Windows uses Edge WebView2, which ships with Windows 11.)\n\n"
    )
    raise

from modules.activity_logger import ActivityLogger
from modules.hotkey_manager import HotkeyManager
from modules.tray_manager import TrayManager
from modules.wfh_controller import WFHController


def _resource_root() -> Path:
    """Return the folder containing bundled resources (works both in dev and frozen exe)."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


UI_DIR = _resource_root() / "ui"
INDEX_HTML = UI_DIR / "index.html"


class Api:
    """Methods on this class are reachable from JS as window.pywebview.api.*"""

    def __init__(self) -> None:
        self.logger = ActivityLogger(log_file="wfh.log")
        self.controller = WFHController(logger=self.logger)
        self._window: webview.Window | None = None
        self._started_at: float | None = None
        self._engine_enabled = {
            "mouse": True,
            "keyboard": True,
            "browser": True,
            "vscode": True,
        }

        self.tray = TrayManager(
            on_show=self._show,
            on_hide=self._hide,
            on_exit=self._exit_app,
        )
        if self.tray.available:
            self.tray.start()
            self.logger.log("SYSTEM", "system tray enabled")
        else:
            self.logger.log("SYSTEM", "system tray unavailable on this environment")

        self.hotkeys = HotkeyManager({
            "<ctrl>+<alt>+s": self._hotkey_start,
            "<ctrl>+<alt>+x": self._hotkey_stop,
            "<ctrl>+<alt>+h": self._hide,
            "<ctrl>+<alt>+o": self._show,
        })
        if self.hotkeys.available:
            self.hotkeys.start()
            self.logger.log("SYSTEM", "global hotkeys registered (Ctrl+Alt+S/X/H/O)")
        else:
            self.logger.log("SYSTEM", "global hotkeys unavailable (pynput not installed)")

        info = self.controller.info
        self.logger.log("SYSTEM", f"Detected platform: {info.system} {info.release}")
        self.logger.log("SYSTEM", f"Active backend chain: {self.controller.input_driver.backend_summary()}")

    # ----- Window binding -----
    def attach_window(self, window: webview.Window) -> None:
        self._window = window

    # ----- Public API exposed to JS -----
    def get_status(self) -> dict:
        info = self.controller.info
        return {
            "running": self.controller.running,
            "speed": self.controller.get_speed(),
            "platform": info.system,
            "platform_detail": f"{info.system} {info.release}",
            "modifier": info.modifier_key,
            "backend_summary": self.controller.input_driver.backend_summary(),
            "controllers": {
                key: (self.controller.running and self._engine_enabled.get(key, True))
                for key in ("mouse", "keyboard", "browser", "vscode")
            },
            "started_at": self._started_at,
        }

    def start(self) -> dict:
        if not self.controller.running:
            for key, enabled in self._engine_enabled.items():
                if not enabled:
                    engine = getattr(self.controller, key, None)
                    if engine and hasattr(engine, "stop"):
                        engine.stop()
            self.controller.start()
            for key, enabled in self._engine_enabled.items():
                if not enabled:
                    engine = getattr(self.controller, key, None)
                    if engine and hasattr(engine, "stop"):
                        engine.stop()
            self._started_at = time.time()
        return self.get_status()

    def stop(self) -> dict:
        if self.controller.running:
            self.controller.stop()
            self._started_at = None
        return self.get_status()

    def set_speed(self, speed: str) -> dict:
        try:
            self.controller.set_speed(speed)
        except ValueError as exc:
            self.logger.log("ERROR", str(exc))
        return self.get_status()

    def toggle_controller(self, key: str, enabled: bool) -> dict:
        if key not in self._engine_enabled:
            return self.get_status()
        self._engine_enabled[key] = bool(enabled)
        engine = getattr(self.controller, key, None)
        if engine is not None:
            if enabled and self.controller.running:
                if hasattr(engine, "start"):
                    engine.start()
            elif not enabled:
                if hasattr(engine, "stop"):
                    engine.stop()
        self.logger.log("SYSTEM", f"{key} {'enabled' if enabled else 'disabled'}")
        return self.get_status()

    def get_recent_logs(self, limit: int = 300) -> list[str]:
        return self.logger.get_recent(limit=limit)

    def check_permissions(self) -> list[str]:
        report = self.controller.permission_report()
        for line in report:
            self.logger.log("PERMISSION", line)
        return report

    def hide_window(self) -> None:
        self._hide()

    def show_window(self) -> None:
        self._show()

    def exit_app(self) -> None:
        self._exit_app()

    # ----- Internal helpers -----
    def _hotkey_start(self) -> None:
        if not self.controller.running:
            self.logger.log("SYSTEM", "hotkey: start automation")
            self.start()

    def _hotkey_stop(self) -> None:
        if self.controller.running:
            self.logger.log("SYSTEM", "hotkey: stop automation")
            self.stop()

    def _hide(self) -> None:
        if self._window:
            try:
                self._window.hide()
                self.logger.log("SYSTEM", "window hidden to tray")
            except Exception as exc:
                self.logger.log("ERROR", f"hide failed: {exc}")

    def _show(self) -> None:
        if self._window:
            try:
                self._window.show()
                self.logger.log("SYSTEM", "window restored")
            except Exception as exc:
                self.logger.log("ERROR", f"show failed: {exc}")

    def _exit_app(self) -> None:
        try:
            self.controller.stop()
        finally:
            self.hotkeys.stop()
            self.tray.stop()
            if self._window:
                try:
                    self._window.destroy()
                except Exception:
                    pass
            os._exit(0)


def main() -> None:
    if not INDEX_HTML.exists():
        sys.stderr.write(f"[!] UI not found at {INDEX_HTML}\n")
        sys.exit(1)

    api = Api()

    window = webview.create_window(
        title="Spotify",
        url=str(INDEX_HTML),
        js_api=api,
        width=1280,
        height=820,
        min_size=(960, 640),
        background_color="#000000",
        resizable=True,
    )
    api.attach_window(window)

    webview.start(debug=False)


if __name__ == "__main__":
    main()
