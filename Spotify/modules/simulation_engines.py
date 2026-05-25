"""Automation engines for mouse, keyboard, browser, and VS Code activity."""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from typing import Callable

from modules.activity_logger import ActivityLogger
from modules.input_backends import CrossPlatformInput, InputBackendError
from modules.platform_manager import PlatformInfo


SPEED_PROFILES = {
    "Basic": {"interval": (5.0, 10.0), "motion_scale": 1.0},
    "Medium": {"interval": (3.0, 7.0), "motion_scale": 0.8},
    "High": {"interval": (2.0, 4.0), "motion_scale": 0.6},
    "Ultra High": {"interval": (1.0, 2.0), "motion_scale": 0.45},
}


@dataclass
class EngineContext:
    info: PlatformInfo
    input_driver: CrossPlatformInput
    logger: ActivityLogger
    get_speed: Callable[[], str]


class BaseEngine:
    name = "base"

    def __init__(self, context: EngineContext) -> None:
        self.ctx = context
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_safe, daemon=True, name=f"{self.name}-engine")
        self._thread.start()
        self.ctx.logger.log(self.name.upper(), "started")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        self.ctx.logger.log(self.name.upper(), "stopped")

    def _run_safe(self) -> None:
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception as exc:
                self.ctx.logger.log_error(self.name, str(exc))
                time.sleep(1.0)

    def wait_interval(self) -> None:
        speed = self.ctx.get_speed()
        profile = SPEED_PROFILES.get(speed, SPEED_PROFILES["Medium"])
        low, high = profile["interval"]
        wait_seconds = random.uniform(low, high)

        end_time = time.time() + wait_seconds
        while time.time() < end_time and not self._stop.is_set():
            time.sleep(0.1)

    def run_once(self) -> None:  # pragma: no cover
        raise NotImplementedError


class MouseEngine(BaseEngine):
    name = "mouse"

    @staticmethod
    def _bezier_points(start: tuple[int, int], end: tuple[int, int], samples: int = 24) -> list[tuple[float, float]]:
        sx, sy = start
        ex, ey = end

        ctrl1 = (sx + random.uniform(-180, 180), sy + random.uniform(-180, 180))
        ctrl2 = (ex + random.uniform(-180, 180), ey + random.uniform(-180, 180))

        points: list[tuple[float, float]] = []
        for i in range(samples + 1):
            t = i / samples
            x = (
                (1 - t) ** 3 * sx
                + 3 * (1 - t) ** 2 * t * ctrl1[0]
                + 3 * (1 - t) * t**2 * ctrl2[0]
                + t**3 * ex
            )
            y = (
                (1 - t) ** 3 * sy
                + 3 * (1 - t) ** 2 * t * ctrl1[1]
                + 3 * (1 - t) * t**2 * ctrl2[1]
                + t**3 * ey
            )
            points.append((x, y))
        return points

    def run_once(self) -> None:
        self.wait_interval()
        if self._stop.is_set():
            return

        width, height = self.ctx.input_driver.size()
        start = self.ctx.input_driver.position()
        target = (
            random.randint(120, max(121, width - 120)),
            random.randint(120, max(121, height - 120)),
        )

        speed = self.ctx.get_speed()
        scale = SPEED_PROFILES.get(speed, SPEED_PROFILES["Medium"])["motion_scale"]
        points = self._bezier_points(start, target, samples=22)

        for x, y in points:
            if self._stop.is_set():
                return
            jitter_x = int(x + random.uniform(-1.5, 1.5))
            jitter_y = int(y + random.uniform(-1.5, 1.5))
            try:
                self.ctx.input_driver.move_to(jitter_x, jitter_y, duration=random.uniform(0.002, 0.009) * scale)
            except InputBackendError as exc:
                self.ctx.logger.log_error("mouse_move", str(exc))
                return
            time.sleep(random.uniform(0.004, 0.012) * scale)

        self.ctx.logger.log("MOUSE", f"move to {target[0]},{target[1]}")

        if random.random() < 0.35:
            time.sleep(random.uniform(0.05, 0.16))
            self.ctx.input_driver.click()
            self.ctx.logger.log("MOUSE", "natural click")

        if random.random() < 0.20:
            amount = random.randint(-4, 4)
            if amount != 0:
                self.ctx.input_driver.scroll(amount)
                self.ctx.logger.log("MOUSE", f"scroll {amount}")


class KeyboardEngine(BaseEngine):
    name = "keyboard"

    def __init__(self, context: EngineContext) -> None:
        super().__init__(context)
        self.primary_modifier = context.info.modifier_key

        keys = ["shift", "ctrl", "pageup", "pagedown", "tab"]
        if context.info.system == "Darwin":
            keys.append("cmd")
        if context.info.system == "Windows":
            keys.append("win")
        self.allowed_keys = keys

        self.combos: list[list[str]] = [
            [self.primary_modifier, "tab"],
            [self.primary_modifier, "shift", "tab"],
            [self.primary_modifier, "pageup"],
            [self.primary_modifier, "pagedown"],
            ["shift", "tab"],
        ]

    def _human_delay(self) -> None:
        time.sleep(random.uniform(0.05, 0.2))

    def run_once(self) -> None:
        self.wait_interval()
        if self._stop.is_set():
            return

        if random.random() < 0.55:
            key = random.choice(self.allowed_keys)
            self.ctx.input_driver.press(key)
            self._human_delay()
            self.ctx.logger.log("KEYBOARD", f"press {key}")
        else:
            combo = random.choice(self.combos)
            self.ctx.input_driver.hotkey(combo)
            self._human_delay()
            self.ctx.logger.log("KEYBOARD", f"combo {'+'.join(combo)}")


class BrowserEngine(BaseEngine):
    name = "browser"

    def __init__(self, context: EngineContext, detect_browsers: Callable[[], list[str]]) -> None:
        super().__init__(context)
        self.detect_browsers = detect_browsers
        self.mod = context.info.modifier_key
        self.window_combo = ["cmd", "tab"] if context.info.system == "Darwin" else ["alt", "tab"]

    def run_once(self) -> None:
        self.wait_interval()
        if self._stop.is_set():
            return

        browsers = self.detect_browsers()
        label = ", ".join(browsers) if browsers else "none detected"
        self.ctx.logger.log("BROWSER", f"active browsers: {label}")

        action = random.choices(
            ["tab_next", "tab_prev", "window_next"],
            weights=[0.5, 0.25, 0.25],
            k=1,
        )[0]

        if action == "tab_next":
            combo = [self.mod, "tab"]
        elif action == "tab_prev":
            combo = [self.mod, "shift", "tab"]
        else:
            combo = self.window_combo

        self.ctx.input_driver.hotkey(combo)
        time.sleep(random.uniform(0.05, 0.2))
        self.ctx.logger.log("BROWSER", f"navigation {'+'.join(combo)}")


class VSCodeEngine(BaseEngine):
    name = "vscode"

    def __init__(self, context: EngineContext) -> None:
        super().__init__(context)
        self.mod = context.info.modifier_key

    def run_once(self) -> None:
        self.wait_interval()
        if self._stop.is_set():
            return

        action = random.choice(["next_tab", "prev_tab", "page_nav"])

        if action == "next_tab":
            combo = [self.mod, "tab"]
            self.ctx.input_driver.hotkey(combo)
            self.ctx.logger.log("VSCODE", f"tab switch {'+'.join(combo)}")
            return

        if action == "prev_tab":
            combo = [self.mod, "shift", "tab"]
            self.ctx.input_driver.hotkey(combo)
            self.ctx.logger.log("VSCODE", f"tab switch {'+'.join(combo)}")
            return

        key = random.choice(["pageup", "pagedown"])
        self.ctx.input_driver.press(key)
        self.ctx.logger.log("VSCODE", f"file navigation {key}")
