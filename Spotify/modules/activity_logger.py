"""Thread-safe activity logging for the WFH automation app."""

from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Callable, Deque, List


LogCallback = Callable[[str], None]


class ActivityLogger:
    """Central logger with in-memory history and callback fanout."""

    def __init__(self, log_file: str = "wfh.log", max_lines: int = 2000) -> None:
        self._lock = threading.Lock()
        self._history: Deque[str] = deque(maxlen=max_lines)
        self._callbacks: List[LogCallback] = []

        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

        self._logger = logging.getLogger("wfh_automation")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        if not self._logger.handlers:
            handler = logging.FileHandler(log_file, encoding="utf-8")
            formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

    def register_callback(self, callback: LogCallback) -> None:
        with self._lock:
            self._callbacks.append(callback)

    def log(self, category: str, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{category}] {message}"

        with self._lock:
            self._history.append(line)
            callbacks = list(self._callbacks)

        self._logger.info("[%s] %s", category, message)

        for callback in callbacks:
            try:
                callback(line)
            except Exception:
                # Logging should never crash the app.
                continue

        print(line)

    def log_activity(self, action_type: str, details: str = "") -> None:
        self.log(action_type, details)

    def log_error(self, error_type: str, error_details: str) -> None:
        self.log(f"ERROR:{error_type}", error_details)

    def get_recent(self, limit: int = 500) -> list[str]:
        with self._lock:
            return list(self._history)[-limit:]
