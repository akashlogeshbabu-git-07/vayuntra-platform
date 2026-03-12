"""
Vayuntra Agent — Process Isolator
Terminates or suspends malicious processes on command from control plane
or triggered by local detection at anomaly score > 0.90.
"""
import os
import signal
import subprocess
from typing import List, Optional

import structlog

log = structlog.get_logger(__name__)


class ProcessIsolator:
    """
    Terminates or suspends processes identified as malicious.
    Supports kill-by-PID, kill-by-name, and process suspension.
    """

    def __init__(self, os_type: str):
        self.os_type = os_type
        self._terminated: List[int] = []

    def kill_pid(self, pid: int, force: bool = False) -> bool:
        """
        Terminate a process by PID.
        Tries SIGTERM first, then SIGKILL (or Windows TerminateProcess).
        """
        log.warning("process_isolator.kill_pid", pid=pid, force=force)
        try:
            import psutil
            proc = psutil.Process(pid)
            proc_name = proc.name()

            if force or self.os_type == "windows":
                proc.kill()
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    proc.kill()

            self._terminated.append(pid)
            log.warning("process_isolator.killed",
                        pid=pid, name=proc_name, method="force" if force else "term")
            return True

        except ImportError:
            return self._kill_pid_fallback(pid, force)
        except Exception as e:
            log.error("process_isolator.kill_error", pid=pid, error=str(e))
            return False

    def kill_by_name(self, process_name: str) -> List[int]:
        """
        Kill all processes matching the given name.
        Returns list of PIDs that were terminated.
        """
        killed_pids = []
        log.warning("process_isolator.kill_by_name", name=process_name)

        try:
            import psutil
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if proc.info["name"] and \
                       proc.info["name"].lower() == process_name.lower():
                        if self.kill_pid(proc.info["pid"], force=True):
                            killed_pids.append(proc.info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except ImportError:
            killed_pids = self._kill_by_name_fallback(process_name)

        return killed_pids

    def suspend_pid(self, pid: int) -> bool:
        """
        Suspend (pause) a process without killing it.
        Useful for forensic preservation before full termination.
        Linux/macOS: SIGSTOP. Windows: SuspendThread via psutil.
        """
        log.warning("process_isolator.suspend", pid=pid)
        try:
            import psutil
            proc = psutil.Process(pid)
            proc.suspend()
            log.info("process_isolator.suspended", pid=pid, name=proc.name())
            return True
        except ImportError:
            if self.os_type != "windows":
                try:
                    os.kill(pid, signal.SIGSTOP)
                    return True
                except Exception:
                    pass
            return False
        except Exception as e:
            log.error("process_isolator.suspend_error", pid=pid, error=str(e))
            return False

    def kill_process_tree(self, pid: int) -> List[int]:
        """
        Kill a process and its entire child tree.
        Prevents malware from spawning survivor processes.
        """
        killed = []
        try:
            import psutil
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            # Kill children first
            for child in children:
                try:
                    child.kill()
                    killed.append(child.pid)
                except psutil.NoSuchProcess:
                    pass
            # Kill parent
            parent.kill()
            killed.append(pid)
            log.warning("process_isolator.tree_killed",
                        root_pid=pid, total_killed=len(killed))
        except Exception as e:
            log.error("process_isolator.tree_kill_error", pid=pid, error=str(e))
        return killed

    def _kill_pid_fallback(self, pid: int, force: bool) -> bool:
        """Fallback using OS commands when psutil unavailable."""
        try:
            if self.os_type == "windows":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                               capture_output=True, timeout=10)
            else:
                sig = "-9" if force else "-15"
                subprocess.run(["kill", sig, str(pid)],
                               capture_output=True, timeout=10)
            return True
        except Exception as e:
            log.error("process_isolator.fallback_error", pid=pid, error=str(e))
            return False

    def _kill_by_name_fallback(self, name: str) -> List[int]:
        """Fallback kill-by-name using OS commands."""
        try:
            if self.os_type == "windows":
                subprocess.run(["taskkill", "/F", "/IM", name],
                               capture_output=True, timeout=10)
            else:
                subprocess.run(["pkill", "-9", "-f", name],
                               capture_output=True, timeout=10)
        except Exception:
            pass
        return []

    @property
    def terminated_pids(self) -> List[int]:
        return list(self._terminated)
