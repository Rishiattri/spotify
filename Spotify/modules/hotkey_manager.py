"""Global hotkey registration with graceful fallback when pynput is missing."""

from __future__ import annotations

from typing import Callable, Mapping


class HotkeyManager:
    def __init__(self, bindings: Mapping[str, Callable[[], None]]) -> None:
        self._bindings = dict(bindings)
        self._listener = None
        self.available = False

        try:
            from pynput import keyboard  # noqa: F401

            self.available = True
        except Exception:
            self.available = False

    def start(self) -> None:
        if not self.available or self._listener is not None:
            return

        from pynput import keyboard

        def _wrap(fn: Callable[[], None]) -> Callable[[], None]:
            def _runner() -> None:
                try:
                    fn()
                except Exception:
                    pass

            return _runner

        mapping = {combo: _wrap(fn) for combo, fn in self._bindings.items()}
        self._listener = keyboard.GlobalHotKeys(mapping)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
