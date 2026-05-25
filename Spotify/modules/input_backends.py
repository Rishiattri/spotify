"""Input backend abstraction with platform-specific fallbacks."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Iterable, Sequence

from modules.activity_logger import ActivityLogger
from modules.platform_manager import PlatformInfo


class InputBackendError(RuntimeError):
    """Raised when a backend action fails."""


class BaseBackend:
    name = "base"
    capabilities: set[str] = set()

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:  # pragma: no cover
        raise InputBackendError(f"{self.name} does not support mouse movement")

    def click(self) -> None:  # pragma: no cover
        raise InputBackendError(f"{self.name} does not support click")

    def scroll(self, amount: int) -> None:  # pragma: no cover
        raise InputBackendError(f"{self.name} does not support scroll")

    def press(self, key: str) -> None:  # pragma: no cover
        raise InputBackendError(f"{self.name} does not support key press")

    def hotkey(self, keys: Sequence[str]) -> None:  # pragma: no cover
        raise InputBackendError(f"{self.name} does not support hotkey")

    def position(self) -> tuple[int, int]:  # pragma: no cover
        raise InputBackendError(f"{self.name} does not support reading mouse position")

    def size(self) -> tuple[int, int]:  # pragma: no cover
        raise InputBackendError(f"{self.name} does not support reading screen size")


class PyAutoGUIBackend(BaseBackend):
    name = "pyautogui"
    capabilities = {"mouse", "keyboard", "screen"}

    KEY_MAP = {
        "cmd": "command",
        "win": "winleft",
    }

    def __init__(self) -> None:
        import pyautogui

        self.pg = pyautogui
        self.pg.FAILSAFE = False
        self.pg.PAUSE = 0.0

    def _map_key(self, key: str) -> str:
        return self.KEY_MAP.get(key, key)

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        self.pg.moveTo(x, y, duration=max(0.0, duration))

    def click(self) -> None:
        self.pg.click()

    def scroll(self, amount: int) -> None:
        self.pg.scroll(amount)

    def press(self, key: str) -> None:
        self.pg.press(self._map_key(key))

    def hotkey(self, keys: Sequence[str]) -> None:
        mapped = [self._map_key(k) for k in keys]
        self.pg.hotkey(*mapped)

    def position(self) -> tuple[int, int]:
        pos = self.pg.position()
        return int(pos.x), int(pos.y)

    def size(self) -> tuple[int, int]:
        size = self.pg.size()
        return int(size.width), int(size.height)


class AppleScriptBackend(BaseBackend):
    name = "applescript"
    capabilities = {"keyboard"}

    KEYCODE = {
        "tab": 48,
        "cmd": 55,
        "shift": 56,
        "ctrl": 59,
        "pageup": 116,
        "pagedown": 121,
    }

    MODIFIERS = {
        "cmd": "command down",
        "shift": "shift down",
        "ctrl": "control down",
    }

    def _run(self, script: str) -> None:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise InputBackendError(result.stderr.strip() or result.stdout.strip() or "AppleScript failed")

    def press(self, key: str) -> None:
        code = self.KEYCODE.get(key)
        if code is None:
            raise InputBackendError(f"Unsupported AppleScript key: {key}")
        script = f'tell application "System Events" to key code {code}'
        self._run(script)

    def hotkey(self, keys: Sequence[str]) -> None:
        if not keys:
            return
        base = keys[-1]
        code = self.KEYCODE.get(base)
        if code is None:
            raise InputBackendError(f"Unsupported AppleScript key: {base}")

        modifiers = [self.MODIFIERS[k] for k in keys[:-1] if k in self.MODIFIERS]
        if modifiers:
            mods = ", ".join(modifiers)
            script = (
                'tell application "System Events" to key code '
                f"{code} using {{{mods}}}"
            )
        else:
            script = f'tell application "System Events" to key code {code}'
        self._run(script)


class CliclickBackend(BaseBackend):
    name = "cliclick"
    capabilities = {"mouse"}

    def _run(self, args: Sequence[str]) -> str:
        result = subprocess.run(["cliclick", *args], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise InputBackendError(result.stderr.strip() or "cliclick failed")
        return result.stdout.strip()

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        self._run([f"m:{x},{y}"])

    def click(self) -> None:
        self._run(["c:."])

    def position(self) -> tuple[int, int]:
        out = self._run(["p"])  # format: "x,y"
        x_str, y_str = out.split(",", maxsplit=1)
        return int(x_str), int(y_str)


class XdotoolBackend(BaseBackend):
    name = "xdotool"
    capabilities = {"mouse", "keyboard"}

    KEY_MAP = {
        "shift": "Shift_L",
        "ctrl": "Control_L",
        "cmd": "Super_L",
        "win": "Super_L",
        "tab": "Tab",
        "pageup": "Page_Up",
        "pagedown": "Page_Down",
    }

    def _run(self, args: Sequence[str]) -> str:
        result = subprocess.run(["xdotool", *args], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise InputBackendError(result.stderr.strip() or "xdotool failed")
        return result.stdout.strip()

    def _map(self, key: str) -> str:
        return self.KEY_MAP.get(key, key)

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        self._run(["mousemove", str(x), str(y)])

    def click(self) -> None:
        self._run(["click", "1"])

    def scroll(self, amount: int) -> None:
        if amount == 0:
            return
        button = "4" if amount > 0 else "5"
        for _ in range(abs(amount)):
            self._run(["click", button])

    def press(self, key: str) -> None:
        self._run(["key", self._map(key)])

    def hotkey(self, keys: Sequence[str]) -> None:
        joined = "+".join(self._map(key) for key in keys)
        self._run(["key", joined])

    def position(self) -> tuple[int, int]:
        output = self._run(["getmouselocation", "--shell"])
        values = dict(item.split("=", maxsplit=1) for item in output.splitlines() if "=" in item)
        return int(values["X"]), int(values["Y"])


class YdotoolBackend(BaseBackend):
    name = "ydotool"
    capabilities = {"mouse", "keyboard"}

    KEY_MAP = {
        "shift": 42,
        "ctrl": 29,
        "cmd": 125,
        "win": 125,
        "pageup": 104,
        "pagedown": 109,
        "tab": 15,
    }

    def _run(self, args: Sequence[str]) -> None:
        result = subprocess.run(["ydotool", *args], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or "ydotool failed"
            raise InputBackendError(message)

    def _press_code(self, code: int) -> None:
        self._run(["key", f"{code}:1", f"{code}:0"])

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        self._run(["mousemove", "--absolute", str(x), str(y)])

    def click(self) -> None:
        self._run(["click", "0xC0"])

    def press(self, key: str) -> None:
        code = self.KEY_MAP.get(key)
        if code is None:
            raise InputBackendError(f"Unsupported ydotool key: {key}")
        self._press_code(code)

    def hotkey(self, keys: Sequence[str]) -> None:
        codes = [self.KEY_MAP.get(k) for k in keys]
        if any(code is None for code in codes):
            raise InputBackendError(f"Unsupported ydotool hotkey: {'+'.join(keys)}")

        events: list[str] = []
        for code in codes:
            events.append(f"{code}:1")
        for code in reversed(codes):
            events.append(f"{code}:0")

        self._run(["key", *events])


@dataclass
class BackendResult:
    used_backend: str
    detail: str


class CrossPlatformInput:
    """Tries multiple backends in order for each action."""

    def __init__(self, info: PlatformInfo, logger: ActivityLogger) -> None:
        self.info = info
        self.logger = logger
        self.backends: list[BaseBackend] = []
        self._pyautogui: BaseBackend | None = None
        self._register_backends()

    def _register_backends(self) -> None:
        if self.info.has_pyautogui:
            try:
                self._pyautogui = PyAutoGUIBackend()
                self.backends.append(self._pyautogui)
            except Exception as exc:
                self.logger.log("BACKEND", f"pyautogui init failed: {exc}")

        if self.info.system == "Darwin":
            self.backends.append(AppleScriptBackend())
            if self.info.has_cliclick:
                self.backends.append(CliclickBackend())

        if self.info.system == "Linux":
            if self.info.has_xdotool:
                self.backends.append(XdotoolBackend())
            if self.info.has_ydotool:
                self.backends.append(YdotoolBackend())

    def backend_summary(self) -> str:
        names = [backend.name for backend in self.backends]
        return ", ".join(names) if names else "none"

    def _attempt(self, method: str, args: Iterable, capability: str) -> BackendResult:
        last_error = "No backend available"
        for backend in self.backends:
            if capability not in backend.capabilities:
                continue
            fn = getattr(backend, method, None)
            if fn is None:
                continue
            try:
                fn(*args)
                return BackendResult(used_backend=backend.name, detail="ok")
            except Exception as exc:
                last_error = f"{backend.name}: {exc}"

        raise InputBackendError(last_error)

    def size(self) -> tuple[int, int]:
        if self._pyautogui is not None:
            return self._pyautogui.size()
        return (1920, 1080)

    def position(self) -> tuple[int, int]:
        for backend in self.backends:
            if "screen" in backend.capabilities or "mouse" in backend.capabilities:
                try:
                    return backend.position()
                except Exception:
                    continue
        return (0, 0)

    def move_to(self, x: int, y: int, duration: float) -> BackendResult:
        return self._attempt("move_to", (int(x), int(y), float(duration)), "mouse")

    def click(self) -> BackendResult:
        return self._attempt("click", (), "mouse")

    def scroll(self, amount: int) -> BackendResult:
        return self._attempt("scroll", (int(amount),), "mouse")

    def press(self, key: str) -> BackendResult:
        return self._attempt("press", (key,), "keyboard")

    def hotkey(self, keys: Sequence[str]) -> BackendResult:
        return self._attempt("hotkey", (list(keys),), "keyboard")


def command_available(command: str) -> bool:
    return shutil.which(command) is not None
