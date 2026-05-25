"""System tray integration with graceful fallback."""

from __future__ import annotations

import threading
from typing import Callable


class TrayManager:
    def __init__(self, on_show: Callable[[], None], on_hide: Callable[[], None], on_exit: Callable[[], None]) -> None:
        self._on_show = on_show
        self._on_hide = on_hide
        self._on_exit = on_exit
        self._icon = None
        self._thread: threading.Thread | None = None
        self.available = False

        try:
            import pystray  # noqa: F401
            from PIL import Image, ImageDraw  # noqa: F401

            self.available = True
        except Exception:
            self.available = False

    def _build_icon(self):
        import pystray
        from PIL import Image, ImageDraw

        image = Image.new("RGB", (64, 64), color=(23, 25, 35))
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 10, 54, 54), outline=(72, 187, 255), width=3)
        draw.rectangle((20, 20, 44, 44), fill=(0, 170, 130))

        menu = pystray.Menu(
            pystray.MenuItem("Show", lambda: self._on_show()),
            pystray.MenuItem("Hide", lambda: self._on_hide()),
            pystray.MenuItem("Exit", lambda: self._on_exit()),
        )

        return pystray.Icon("wfh_assistant", image, "WFH Assistant", menu)

    def start(self) -> None:
        if not self.available or self._thread:
            return

        def runner() -> None:
            self._icon = self._build_icon()
            self._icon.run()

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()
            self._icon = None
        self._thread = None
