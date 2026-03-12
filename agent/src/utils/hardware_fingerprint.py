"""
Vayuntra Agent — Hardware Fingerprint
Generates a stable, unique hardware fingerprint for agent identity verification.
Used to detect agent cloning and unauthorized agent migrations.
"""
import hashlib
import platform
import uuid
from typing import Optional

import structlog

log = structlog.get_logger(__name__)


def get_hardware_fingerprint() -> str:
    """
    Generate a stable hardware fingerprint from:
    - CPU info
    - MAC address (primary NIC)
    - Machine UUID (if available)
    - Hostname
    Returns a SHA-256 hex digest (64 chars).
    """
    components = []

    # Hostname
    try:
        components.append(f"host:{platform.node()}")
    except Exception:
        pass

    # CPU identifier
    try:
        components.append(f"cpu:{platform.processor()}")
    except Exception:
        pass

    # MAC address of primary interface
    try:
        mac = uuid.getnode()
        # uuid.getnode() returns a 48-bit integer
        mac_str = ":".join(
            f"{(mac >> (i * 8)) & 0xFF:02x}" for i in reversed(range(6))
        )
        components.append(f"mac:{mac_str}")
    except Exception:
        pass

    # Machine UUID (Linux: /etc/machine-id, Windows: registry, macOS: IOKit)
    machine_id = _get_machine_id()
    if machine_id:
        components.append(f"mid:{machine_id}")

    # OS platform
    try:
        components.append(f"os:{platform.system()}:{platform.release()}")
    except Exception:
        pass

    if not components:
        # Absolute fallback — not stable across reboots
        components.append(f"fallback:{uuid.uuid4().hex}")
        log.warning("hardware_fingerprint.fallback_used")

    raw = "|".join(sorted(components))
    fingerprint = hashlib.sha256(raw.encode()).hexdigest()
    log.debug("hardware_fingerprint.generated",
              components=len(components), fp_prefix=fingerprint[:8])
    return fingerprint


def _get_machine_id() -> Optional[str]:
    """Read OS-provided persistent machine ID."""
    # Linux
    for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
        try:
            with open(path) as f:
                mid = f.read().strip()
            if mid:
                return mid
        except Exception:
            pass

    # macOS — IOPlatformUUID
    if platform.system() == "Darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if "IOPlatformUUID" in line:
                    parts = line.split('"')
                    if len(parts) >= 4:
                        return parts[-2]
        except Exception:
            pass

    # Windows — MachineGuid from registry
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            )
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(guid)
        except Exception:
            pass

    return None
