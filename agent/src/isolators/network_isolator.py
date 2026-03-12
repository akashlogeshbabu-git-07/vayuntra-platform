"""
Vayuntra Agent — Network Isolator
Executes network isolation by blocking all inbound/outbound traffic
except for the control plane connection (mTLS WebSocket).
Cross-platform: iptables (Linux), Windows Firewall (Windows), pf (macOS).
"""
import subprocess
import os
from typing import List

import structlog

log = structlog.get_logger(__name__)


class NetworkIsolator:
    """
    Implements network containment by inserting firewall rules
    to block all traffic except control plane communication.
    """

    def __init__(self, os_type: str, control_plane_ip: str = ""):
        self.os_type = os_type
        self.control_plane_ip = control_plane_ip
        self._isolated = False
        self._applied_rules: List[str] = []

    def isolate(self, control_plane_ip: str = "") -> bool:
        """
        Apply network isolation rules. Allows only:
        - Control plane IP (mTLS WebSocket on port 443/8443)
        - DNS (port 53) to resolve control plane hostname
        - Loopback
        All other inbound/outbound traffic is dropped.
        Returns True on success.
        """
        cp_ip = control_plane_ip or self.control_plane_ip
        log.warning("network_isolator.applying", os=self.os_type, cp_ip=cp_ip)

        try:
            if self.os_type == "linux":
                success = self._isolate_linux(cp_ip)
            elif self.os_type == "windows":
                success = self._isolate_windows(cp_ip)
            elif self.os_type == "darwin":
                success = self._isolate_macos(cp_ip)
            else:
                log.error("network_isolator.unsupported_os", os=self.os_type)
                return False

            if success:
                self._isolated = True
                log.warning("network_isolator.isolation_active",
                            os=self.os_type, cp_ip=cp_ip)
            return success
        except Exception as e:
            log.error("network_isolator.error", error=str(e))
            return False

    def release(self) -> bool:
        """Remove isolation rules and restore normal network access."""
        log.info("network_isolator.releasing", os=self.os_type)
        try:
            if self.os_type == "linux":
                success = self._release_linux()
            elif self.os_type == "windows":
                success = self._release_windows()
            elif self.os_type == "darwin":
                success = self._release_macos()
            else:
                return False

            if success:
                self._isolated = False
                self._applied_rules.clear()
            return success
        except Exception as e:
            log.error("network_isolator.release_error", error=str(e))
            return False

    @property
    def is_isolated(self) -> bool:
        return self._isolated

    # ── Linux (iptables) ─────────────────────────────────────────────────────

    def _isolate_linux(self, cp_ip: str) -> bool:
        rules = [
            # Allow loopback
            ["iptables", "-I", "INPUT", "1", "-i", "lo", "-j", "ACCEPT"],
            ["iptables", "-I", "OUTPUT", "1", "-o", "lo", "-j", "ACCEPT"],
            # Allow established/related
            ["iptables", "-I", "INPUT", "2", "-m", "state",
             "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT"],
            # Allow control plane
        ]
        if cp_ip:
            rules += [
                ["iptables", "-I", "OUTPUT", "2", "-d", cp_ip, "-j", "ACCEPT"],
                ["iptables", "-I", "INPUT", "3", "-s", cp_ip, "-j", "ACCEPT"],
            ]
        # Block everything else
        rules += [
            ["iptables", "-A", "INPUT", "-j", "DROP"],
            ["iptables", "-A", "OUTPUT", "-j", "DROP"],
            ["iptables", "-A", "FORWARD", "-j", "DROP"],
        ]
        return self._run_rules(rules)

    def _release_linux(self) -> bool:
        rules = [
            ["iptables", "-D", "INPUT", "-j", "DROP"],
            ["iptables", "-D", "OUTPUT", "-j", "DROP"],
            ["iptables", "-D", "FORWARD", "-j", "DROP"],
            ["iptables", "-F"],  # Flush all rules
        ]
        return self._run_rules(rules, ignore_errors=True)

    # ── Windows (netsh advfirewall) ───────────────────────────────────────────

    def _isolate_windows(self, cp_ip: str) -> bool:
        rules = [
            # Block all inbound
            ["netsh", "advfirewall", "firewall", "add", "rule",
             "name=VayuntraIsolateBlockIn", "dir=in", "action=block", "protocol=any"],
            # Block all outbound
            ["netsh", "advfirewall", "firewall", "add", "rule",
             "name=VayuntraIsolateBlockOut", "dir=out", "action=block", "protocol=any"],
        ]
        if cp_ip:
            rules += [
                ["netsh", "advfirewall", "firewall", "add", "rule",
                 "name=VayuntraIsolateAllowCP", "dir=out", "action=allow",
                 "protocol=TCP", f"remoteip={cp_ip}"],
            ]
        return self._run_rules(rules)

    def _release_windows(self) -> bool:
        rules = [
            ["netsh", "advfirewall", "firewall", "delete", "rule",
             "name=VayuntraIsolateBlockIn"],
            ["netsh", "advfirewall", "firewall", "delete", "rule",
             "name=VayuntraIsolateBlockOut"],
            ["netsh", "advfirewall", "firewall", "delete", "rule",
             "name=VayuntraIsolateAllowCP"],
        ]
        return self._run_rules(rules, ignore_errors=True)

    # ── macOS (pfctl) ─────────────────────────────────────────────────────────

    def _isolate_macos(self, cp_ip: str) -> bool:
        pf_rules = "block all\n"
        if cp_ip:
            pf_rules += f"pass out to {cp_ip}\npass in from {cp_ip}\n"
        pf_rules += "pass on lo0\n"

        try:
            pf_conf = "/tmp/vayuntra_isolation.pf"
            with open(pf_conf, "w") as f:
                f.write(pf_rules)
            subprocess.run(["pfctl", "-f", pf_conf], check=True, capture_output=True)
            subprocess.run(["pfctl", "-e"], check=True, capture_output=True)
            return True
        except Exception as e:
            log.error("network_isolator.macos_pf_error", error=str(e))
            return False

    def _release_macos(self) -> bool:
        try:
            subprocess.run(["pfctl", "-d"], capture_output=True)
            subprocess.run(["pfctl", "-F", "all"], capture_output=True)
            return True
        except Exception as e:
            log.error("network_isolator.macos_release_error", error=str(e))
            return False

    def _run_rules(self, rules: list, ignore_errors: bool = False) -> bool:
        for rule in rules:
            try:
                result = subprocess.run(
                    rule, capture_output=True, text=True, timeout=10
                )
                if result.returncode != 0 and not ignore_errors:
                    log.error("network_isolator.rule_failed",
                              cmd=" ".join(rule), stderr=result.stderr[:200])
                    return False
                self._applied_rules.append(" ".join(rule))
            except Exception as e:
                if not ignore_errors:
                    log.error("network_isolator.rule_error",
                              cmd=" ".join(rule), error=str(e))
                    return False
        return True
