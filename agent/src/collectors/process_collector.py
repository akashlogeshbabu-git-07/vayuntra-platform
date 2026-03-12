"""
Vayuntra Agent — Process Collector
Collects running process telemetry cross-platform using psutil.
"""
import os
import platform
import time
from typing import Any, Dict, List

import structlog

log = structlog.get_logger(__name__)


class ProcessCollector:
    """Collects process-level telemetry from the host OS."""

    def __init__(self, os_type: str):
        self.os_type = os_type

    def collect(self) -> List[Dict[str, Any]]:
        """Return list of process snapshots."""
        try:
            import psutil
        except ImportError:
            log.warning("process_collector.psutil_missing")
            return []

        processes = []
        try:
            for proc in psutil.process_iter([
                "pid", "name", "exe", "cmdline", "username",
                "create_time", "status", "ppid", "num_threads",
            ]):
                try:
                    info = proc.info
                    age_seconds = time.time() - (info.get("create_time") or time.time())
                    elevated = self._is_elevated(proc)
                    signed = self._is_signed(info.get("exe") or "")
                    tree_depth = self._estimate_tree_depth(proc)

                    processes.append({
                        "pid": info["pid"],
                        "name": info["name"] or "",
                        "exe": info.get("exe") or "",
                        "cmdline": " ".join(info.get("cmdline") or [])[:512],
                        "username": info.get("username") or "",
                        "age_seconds": int(age_seconds),
                        "status": info.get("status") or "",
                        "ppid": info.get("ppid") or 0,
                        "num_threads": info.get("num_threads") or 1,
                        "elevated": elevated,
                        "signed": signed,
                        "tree_depth": tree_depth,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            log.error("process_collector.error", error=str(e))

        return processes

    def _is_elevated(self, proc) -> bool:
        """Check if process runs with elevated privileges."""
        try:
            import psutil
            if self.os_type == "windows":
                return False  # Requires win32api; conservative default
            uids = proc.uids()
            return uids.effective == 0
        except Exception:
            return False

    def _is_signed(self, exe_path: str) -> bool:
        """
        Basic signed binary heuristic.
        On Windows, system32 binaries are considered signed.
        Full Authenticode verification requires win32security.
        """
        if not exe_path:
            return True  # Unknown — assume signed (conservative)
        system_paths = [
            "/usr/bin", "/usr/sbin", "/bin", "/sbin",          # Linux
            "C:\\Windows\\System32", "C:\\Windows\\SysWOW64",   # Windows
            "/System/Library", "/usr/libexec",                  # macOS
        ]
        return any(exe_path.startswith(p) for p in system_paths)

    def _estimate_tree_depth(self, proc) -> int:
        """Walk parent chain to estimate process tree depth."""
        try:
            import psutil
            depth = 0
            p = proc
            visited = set()
            while True:
                pid = p.pid
                if pid in visited or pid <= 1:
                    break
                visited.add(pid)
                ppid = p.ppid()
                if ppid == 0 or ppid == pid:
                    break
                p = psutil.Process(ppid)
                depth += 1
                if depth > 10:
                    break
            return depth
        except Exception:
            return 0
