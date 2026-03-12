"""
Vayuntra Agent — Auth/Login Event Collector
Collects authentication events: failed logins, privilege escalations,
sudo/su usage, and off-hours login patterns.
"""
import os
import platform
import re
import subprocess
import time
from typing import Any, Dict

import structlog

log = structlog.get_logger(__name__)


class AuthCollector:
    """
    Collects authentication telemetry.
    Linux: parses /var/log/auth.log or journald.
    Windows: queries Security Event Log via wevtutil.
    macOS: queries unified log for authentication events.
    """

    def __init__(self, os_type: str):
        self.os_type = os_type
        self._last_collect_time = time.time() - 60  # Start with 60s lookback

    def collect(self) -> Dict[str, Any]:
        """Return auth telemetry since last collection."""
        result = {
            "failed_attempts": 0,
            "priv_escalations": 0,
            "successful_logins": 0,
            "off_hours_logins": 0,
            "sudo_events": 0,
            "new_user_created": 0,
        }

        try:
            if self.os_type == "linux":
                result = self._collect_linux()
            elif self.os_type == "windows":
                result = self._collect_windows()
            elif self.os_type == "darwin":
                result = self._collect_macos()
        except Exception as e:
            log.error("auth_collector.error", os=self.os_type, error=str(e))

        self._last_collect_time = time.time()
        return result

    def _collect_linux(self) -> Dict[str, Any]:
        failed = 0
        priv_esc = 0
        sudo_events = 0
        successful = 0
        off_hours = 0
        new_users = 0

        # Try journald first, fall back to auth.log
        log_lines = self._read_journald_auth() or self._read_auth_log()

        hour = time.localtime().tm_hour
        is_off_hours = hour < 7 or hour > 20

        for line in log_lines:
            if "Failed password" in line or "authentication failure" in line:
                failed += 1
            if "Accepted password" in line or "Accepted publickey" in line:
                successful += 1
                if is_off_hours:
                    off_hours += 1
            if "sudo:" in line:
                sudo_events += 1
            if "su:" in line and "FAILED" not in line:
                priv_esc += 1
            if "useradd" in line or "new user" in line.lower():
                new_users += 1

        return {
            "failed_attempts": failed,
            "priv_escalations": priv_esc,
            "successful_logins": successful,
            "off_hours_logins": off_hours,
            "sudo_events": sudo_events,
            "new_user_created": new_users,
        }

    def _read_journald_auth(self):
        """Read auth events from journald for the last 60 seconds."""
        try:
            result = subprocess.run(
                ["journalctl", "_COMM=sshd", "_COMM=sudo", "_COMM=su",
                 "--since", "60 seconds ago", "--no-pager", "-q"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.splitlines() if result.returncode == 0 else []
        except Exception:
            return []

    def _read_auth_log(self):
        """Read from /var/log/auth.log as fallback."""
        auth_log_paths = ["/var/log/auth.log", "/var/log/secure"]
        for path in auth_log_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", errors="replace") as f:
                        lines = f.readlines()
                    # Return last 500 lines (recent events)
                    return lines[-500:]
                except PermissionError:
                    pass
        return []

    def _collect_windows(self) -> Dict[str, Any]:
        """
        Parse Windows Security Event Log for auth events.
        Event IDs: 4625=Failed Login, 4624=Success, 4672=Priv Assigned,
                   4720=User Created, 4732=Added to Admin Group.
        """
        failed = 0
        successful = 0
        priv_esc = 0
        new_users = 0

        try:
            result = subprocess.run(
                ["wevtutil", "qe", "Security",
                 "/q:*[System[(EventID=4625 or EventID=4624 or EventID=4672 or EventID=4720)]]",
                 "/c:100", "/rd:true", "/f:text"],
                capture_output=True, text=True, timeout=10,
            )
            output = result.stdout
            failed = output.count("Event ID: 4625")
            successful = output.count("Event ID: 4624")
            priv_esc = output.count("Event ID: 4672")
            new_users = output.count("Event ID: 4720")
        except Exception as e:
            log.debug("auth_collector.windows_evtlog_error", error=str(e))

        hour = time.localtime().tm_hour
        return {
            "failed_attempts": failed,
            "priv_escalations": priv_esc,
            "successful_logins": successful,
            "off_hours_logins": successful if (hour < 7 or hour > 20) else 0,
            "sudo_events": 0,
            "new_user_created": new_users,
        }

    def _collect_macos(self) -> Dict[str, Any]:
        """Parse macOS unified log for auth events."""
        failed = 0
        successful = 0
        sudo_events = 0

        try:
            result = subprocess.run(
                ["log", "show", "--predicate",
                 'process == "sshd" OR process == "sudo" OR process == "loginwindow"',
                 "--last", "1m", "--style", "compact"],
                capture_output=True, text=True, timeout=10,
            )
            for line in result.stdout.splitlines():
                if "failed" in line.lower() or "invalid" in line.lower():
                    failed += 1
                if "accepted" in line.lower() or "authenticated" in line.lower():
                    successful += 1
                if "sudo" in line.lower():
                    sudo_events += 1
        except Exception as e:
            log.debug("auth_collector.macos_log_error", error=str(e))

        hour = time.localtime().tm_hour
        return {
            "failed_attempts": failed,
            "priv_escalations": 0,
            "successful_logins": successful,
            "off_hours_logins": successful if (hour < 7 or hour > 20) else 0,
            "sudo_events": sudo_events,
            "new_user_created": 0,
        }
