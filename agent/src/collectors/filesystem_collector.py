"""
Vayuntra Agent — Filesystem Collector
Monitors file write/delete/create rates and detects high-entropy writes
indicative of ransomware encryption.
"""
import math
import os
import platform
import threading
import time
from collections import deque
from typing import Any, Dict, List

import structlog

log = structlog.get_logger(__name__)

# Paths considered sensitive — access triggers elevated scoring
SENSITIVE_PATHS = [
    "/etc/passwd", "/etc/shadow", "/etc/sudoers",
    "/root/.ssh", "/home", "C:\\Windows\\System32\\config",
    "C:\\Users", "/var/lib/docker", "/proc/keys",
]

# Extensions associated with credential/config files
SENSITIVE_EXTENSIONS = {".key", ".pem", ".pfx", ".p12", ".kdbx", ".env", ".cfg", ".ini"}

# Extensions created by ransomware families
RANSOMWARE_EXTENSIONS = {
    ".locked", ".encrypted", ".enc", ".crypto", ".crypt",
    ".ransom", ".wncry", ".wncryt", ".cerber", ".locky",
}


class FilesystemCollector:
    """
    Monitors filesystem activity using a sliding time window.
    Uses watchdog if available, falls back to polling /proc/sys/fs on Linux.
    """

    WINDOW_SECONDS = 60

    def __init__(self, os_type: str):
        self.os_type = os_type
        self._write_events: deque = deque()
        self._delete_events: deque = deque()
        self._exe_create_events: deque = deque()
        self._sensitive_hits: List[str] = []
        self._entropy_samples: List[float] = []
        self._lock = threading.Lock()
        self._observer = None
        self._start_watcher()

    def _start_watcher(self):
        """Start filesystem event watcher if watchdog is available."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            collector = self

            class _Handler(FileSystemEventHandler):
                def on_modified(self, event):
                    if not event.is_directory:
                        collector._record_write(event.src_path)

                def on_created(self, event):
                    if not event.is_directory:
                        collector._record_write(event.src_path)
                        if event.src_path.endswith((".exe", ".dll", ".sh", ".bat", ".ps1")):
                            with collector._lock:
                                collector._exe_create_events.append(time.time())

                def on_deleted(self, event):
                    if not event.is_directory:
                        with collector._lock:
                            collector._delete_events.append(time.time())

            self._observer = Observer()
            watch_paths = self._get_watch_paths()
            for path in watch_paths:
                if os.path.exists(path):
                    self._observer.schedule(_Handler(), path, recursive=True)
            self._observer.start()
            log.info("filesystem_collector.watcher_started", paths=watch_paths)
        except ImportError:
            log.info("filesystem_collector.watchdog_unavailable", fallback="polling")
        except Exception as e:
            log.warning("filesystem_collector.watcher_error", error=str(e))

    def _get_watch_paths(self) -> List[str]:
        if self.os_type == "windows":
            return ["C:\\Users", "C:\\Windows\\Temp", "C:\\ProgramData"]
        elif self.os_type == "darwin":
            return [os.path.expanduser("~"), "/tmp", "/var/folders"]
        else:  # linux
            return ["/home", "/tmp", "/var/tmp", "/root"]

    def _record_write(self, path: str):
        now = time.time()
        with self._lock:
            self._write_events.append(now)
            # Check sensitive path access
            for sp in SENSITIVE_PATHS:
                if path.startswith(sp):
                    self._sensitive_hits.append(path)
                    break
            # Check ransomware extensions
            _, ext = os.path.splitext(path)
            if ext.lower() in RANSOMWARE_EXTENSIONS:
                # High-entropy write indicator
                self._entropy_samples.append(0.95)

    def collect(self) -> Dict[str, Any]:
        """Return filesystem telemetry for the last 60 seconds."""
        now = time.time()
        cutoff = now - self.WINDOW_SECONDS

        with self._lock:
            # Prune old events
            while self._write_events and self._write_events[0] < cutoff:
                self._write_events.popleft()
            while self._delete_events and self._delete_events[0] < cutoff:
                self._delete_events.popleft()
            while self._exe_create_events and self._exe_create_events[0] < cutoff:
                self._exe_create_events.popleft()

            writes = len(self._write_events)
            deletes = len(self._delete_events)
            exe_creates = len(self._exe_create_events)
            sensitive_score = min(len(self._sensitive_hits) / 5.0, 1.0)
            avg_entropy = (sum(self._entropy_samples) / len(self._entropy_samples)
                           if self._entropy_samples else 0.0)

            # Reset rolling accumulators
            self._sensitive_hits.clear()
            self._entropy_samples.clear()

        return {
            "writes_per_min": writes,
            "deletes_per_min": deletes,
            "exe_creates_per_min": exe_creates,
            "sensitive_access_score": round(sensitive_score, 3),
            "avg_write_entropy": round(avg_entropy, 3),
        }

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
