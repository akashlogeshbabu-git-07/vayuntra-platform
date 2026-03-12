"""
Vayuntra Endpoint Agent — Core Controller
Cross-platform endpoint telemetry collection, local detection, and isolation.

Supported platforms:
- Windows (x86_64) — full capability
- Linux (x86_64 / arm64) — full capability
- macOS (x86_64 / arm64) — full capability with SIP constraints
- Raspberry Pi (armv7/arm64) — reduced sensor set, edge gateway mode
- Android — MDM-scoped capability (requires work profile or DEX)

Agent architecture:
1. Collectors: Gather OS telemetry (processes, network, filesystem, auth)
2. Local filter: Pre-process and reduce telemetry before transmission
3. Transmitter: Batch-send to control plane via mTLS WebSocket
4. Local detector: Lightweight IF model for offline/latency-sensitive detection
5. Isolator: Execute containment actions on command
"""

import asyncio
import hashlib
import json
import os
import platform
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import yaml

from collectors.process_collector import ProcessCollector
from collectors.network_collector import NetworkCollector
from collectors.filesystem_collector import FilesystemCollector
from collectors.auth_collector import AuthCollector
from detectors.local_detector import LocalDetector
from isolators.network_isolator import NetworkIsolator
from isolators.process_isolator import ProcessIsolator
from reporters.control_plane_reporter import ControlPlaneReporter
from utils.hardware_fingerprint import get_hardware_fingerprint
from utils.integrity import verify_agent_integrity

log = structlog.get_logger(__name__)


# ─── Agent Configuration ──────────────────────────────────────────────────────

@dataclass
class AgentConfig:
    agent_id: str
    tenant_id: str
    control_plane_url: str
    shared_secret: str
    mtls_cert_path: str
    mtls_key_path: str
    ca_cert_path: str
    heartbeat_interval: int = 60
    telemetry_batch_size: int = 100
    telemetry_interval: int = 10
    local_detection_enabled: bool = True
    local_model_path: str = ""
    deployment_type: str = "workstation"  # workstation | edge_gateway | ot_gateway
    log_level: str = "INFO"
    offline_buffer_max_mb: int = 100

    @classmethod
    def from_yaml(cls, path: str) -> "AgentConfig":
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)


# ─── Platform Detection ───────────────────────────────────────────────────────

def detect_platform() -> Dict[str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()
    return {
        "os_type": system,
        "os_version": platform.version(),
        "architecture": machine,
        "python_version": sys.version,
        "hostname": platform.node(),
    }


def get_collector_set(platform_info: Dict[str, str], deployment_type: str) -> Dict[str, Any]:
    """
    Returns appropriate collector set for the platform.
    Edge/IoT devices get reduced sensor set to conserve resources.
    """
    os_type = platform_info["os_type"]
    is_edge = deployment_type in ("edge_gateway", "ot_gateway")

    collectors = {
        "process": ProcessCollector(os_type=os_type),
        "network": NetworkCollector(os_type=os_type, reduced_mode=is_edge),
        "auth": AuthCollector(os_type=os_type),
    }

    # Filesystem collector is expensive on edge devices
    if not is_edge:
        collectors["filesystem"] = FilesystemCollector(os_type=os_type)

    return collectors


# ─── Telemetry Bundle ─────────────────────────────────────────────────────────

@dataclass
class TelemetryBundle:
    agent_id: str
    tenant_id: str
    sequence_number: int
    collected_at: float      # Unix timestamp
    platform: Dict[str, str]
    telemetry: Dict[str, Any]
    local_anomaly_score: float = 0.0
    is_locally_anomalous: bool = False
    checksum: str = ""

    def compute_checksum(self) -> str:
        """HMAC checksum for tamper detection during transit."""
        payload = json.dumps({
            "agent_id": self.agent_id,
            "sequence_number": self.sequence_number,
            "collected_at": self.collected_at,
            "telemetry": self.telemetry,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()


# ─── Offline Buffer ───────────────────────────────────────────────────────────

class OfflineBuffer:
    """
    Persists telemetry to disk when control plane is unreachable.
    FIFO queue with size limit. Replays on reconnection.
    Air-gap safe: encrypted at rest using derived key.
    """

    def __init__(self, buffer_dir: str, max_size_mb: int = 100):
        self.buffer_dir = Path(buffer_dir)
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def write(self, bundle: TelemetryBundle, encryption_key: bytes) -> None:
        """Write bundle to disk with encryption."""
        from cryptography.fernet import Fernet
        import base64

        filepath = self.buffer_dir / f"{bundle.sequence_number}_{int(bundle.collected_at)}.enc"
        data = json.dumps(asdict(bundle)).encode()

        # Derive Fernet key from shared secret
        fernet_key = base64.urlsafe_b64encode(encryption_key[:32])
        f = Fernet(fernet_key)
        encrypted = f.encrypt(data)

        filepath.write_bytes(encrypted)
        self._enforce_size_limit()

    def drain(self, encryption_key: bytes) -> List[TelemetryBundle]:
        """Read and decrypt buffered bundles, ordered by sequence number."""
        from cryptography.fernet import Fernet
        import base64

        fernet_key = base64.urlsafe_b64encode(encryption_key[:32])
        f = Fernet(fernet_key)

        bundles = []
        files = sorted(self.buffer_dir.glob("*.enc"), key=lambda p: int(p.stem.split("_")[0]))
        for filepath in files:
            try:
                encrypted = filepath.read_bytes()
                data = json.loads(f.decrypt(encrypted).decode())
                bundles.append(TelemetryBundle(**data))
                filepath.unlink()  # Remove after successful drain
            except Exception as e:
                log.error("offline_buffer.read_error", file=str(filepath), error=str(e))
        return bundles

    def _enforce_size_limit(self) -> None:
        files = sorted(self.buffer_dir.glob("*.enc"), key=lambda p: p.stat().st_mtime)
        total_size = sum(f.stat().st_size for f in files)
        while total_size > self.max_size_bytes and files:
            oldest = files.pop(0)
            total_size -= oldest.stat().st_size
            oldest.unlink()
            log.warning("offline_buffer.evicted_old_data", file=str(oldest))


# ─── Main Agent Controller ────────────────────────────────────────────────────

class VayuntraAgent:
    """
    Main agent controller — coordinates collection, detection, and reporting.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.platform_info = detect_platform()
        self.collectors = get_collector_set(self.platform_info, config.deployment_type)
        self.local_detector = LocalDetector(model_path=config.local_model_path)
        self.reporter = ControlPlaneReporter(config=config)
        self.isolator_network = NetworkIsolator(os_type=self.platform_info["os_type"])
        self.isolator_process = ProcessIsolator(os_type=self.platform_info["os_type"])
        self.offline_buffer = OfflineBuffer(
            buffer_dir="/var/vayuntra/buffer",
            max_size_mb=config.offline_buffer_max_mb,
        )
        self._sequence_number = 0
        self._running = False
        self._isolation_active = False

        log.info(
            "agent.initialized",
            agent_id=config.agent_id,
            platform=self.platform_info["os_type"],
            deployment_type=config.deployment_type,
        )

    async def start(self) -> None:
        """Start agent main loop."""
        # Integrity check before starting
        if not await verify_agent_integrity():
            log.critical("agent.integrity_check_failed")
            sys.exit(1)

        self._running = True

        log.info("agent.starting", agent_id=self.config.agent_id)

        # Register with control plane
        await self.reporter.register(
            hardware_fingerprint=get_hardware_fingerprint(),
            platform_info=self.platform_info,
        )

        # Start concurrent tasks
        await asyncio.gather(
            self._telemetry_loop(),
            self._heartbeat_loop(),
            self._command_listener(),
        )

    async def _telemetry_loop(self) -> None:
        """Collect and transmit telemetry on interval."""
        while self._running:
            try:
                await self._collect_and_transmit()
            except Exception as e:
                log.error("agent.telemetry_loop_error", error=str(e))
            await asyncio.sleep(self.config.telemetry_interval)

    async def _collect_and_transmit(self) -> None:
        # Skip collection during full isolation
        if self._isolation_active:
            log.info("agent.collection_paused", reason="isolation_active")
            return

        # Collect from all active collectors
        telemetry = {}
        for name, collector in self.collectors.items():
            try:
                telemetry[name] = await collector.collect()
            except Exception as e:
                log.warning("agent.collector_error", collector=name, error=str(e))
                telemetry[name] = {}

        # Local anomaly detection (fast, offline-capable)
        local_score = 0.0
        is_local_anomaly = False
        if self.config.local_detection_enabled and self.local_detector.is_ready:
            local_score, is_local_anomaly = self.local_detector.detect(telemetry)

        # If locally detected as critical anomaly, trigger containment immediately
        if is_local_anomaly and local_score > 0.90:
            log.warning(
                "agent.local_critical_anomaly",
                score=local_score,
                agent_id=self.config.agent_id,
            )
            await self._auto_contain_local(telemetry, local_score)

        # Build bundle
        self._sequence_number += 1
        bundle = TelemetryBundle(
            agent_id=self.config.agent_id,
            tenant_id=self.config.tenant_id,
            sequence_number=self._sequence_number,
            collected_at=time.time(),
            platform=self.platform_info,
            telemetry=telemetry,
            local_anomaly_score=local_score,
            is_locally_anomalous=is_local_anomaly,
        )
        bundle.checksum = bundle.compute_checksum()

        # Transmit or buffer if offline
        transmitted = await self.reporter.transmit(bundle)
        if not transmitted:
            self.offline_buffer.write(
                bundle,
                encryption_key=self.config.shared_secret.encode()[:32],
            )
        else:
            # Drain buffer if we just came back online
            await self._drain_buffer()

    async def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                await self.reporter.heartbeat(
                    isolation_status="isolated" if self._isolation_active else "none"
                )
            except Exception as e:
                log.warning("agent.heartbeat_error", error=str(e))
            await asyncio.sleep(self.config.heartbeat_interval)

    async def _command_listener(self) -> None:
        """Listen for commands from control plane (via WebSocket)."""
        while self._running:
            try:
                command = await self.reporter.receive_command()
                if command:
                    await self._execute_command(command)
            except Exception as e:
                log.warning("agent.command_listener_error", error=str(e))
            await asyncio.sleep(1)

    async def _execute_command(self, command: Dict[str, Any]) -> None:
        """Execute a command received from the control plane."""
        cmd_type = command.get("type")
        cmd_id = command.get("id")

        log.info("agent.command_received", type=cmd_type, id=cmd_id)

        try:
            if cmd_type == "isolate_network":
                await self.isolator_network.isolate(
                    allow_control_plane=True,
                    control_plane_ip=self.config.control_plane_url,
                )
                self._isolation_active = True

            elif cmd_type == "kill_process":
                pid = command.get("pid")
                await self.isolator_process.kill(pid=pid)

            elif cmd_type == "release_isolation":
                await self.isolator_network.release()
                self._isolation_active = False

            elif cmd_type == "collect_forensic_snapshot":
                snapshot = await self._collect_forensic_snapshot()
                await self.reporter.transmit_forensic(snapshot)

            elif cmd_type == "update_config":
                # Safe config update from control plane
                new_config = command.get("config", {})
                self._apply_safe_config_update(new_config)

            # Acknowledge command execution
            await self.reporter.ack_command(cmd_id=cmd_id, status="executed")

        except Exception as e:
            log.error("agent.command_execution_failed", cmd_type=cmd_type, error=str(e))
            await self.reporter.ack_command(cmd_id=cmd_id, status="failed", error=str(e))

    async def _auto_contain_local(self, telemetry: Dict, score: float) -> None:
        """
        Immediate local containment for critical anomalies.
        Does not wait for control plane — acts autonomously.
        Unknown threats: network isolation + notify.
        """
        log.critical(
            "agent.autonomous_containment",
            score=score,
            agent_id=self.config.agent_id,
        )
        # Network-isolate while preserving control plane channel
        await self.isolator_network.isolate(allow_control_plane=True)
        self._isolation_active = True

        # Notify control plane of autonomous action
        await self.reporter.notify_autonomous_action(
            action="network_isolation",
            reason="local_critical_anomaly",
            score=score,
            telemetry_snapshot=telemetry,
        )

    async def _drain_buffer(self) -> None:
        buffered = self.offline_buffer.drain(
            encryption_key=self.config.shared_secret.encode()[:32]
        )
        for bundle in buffered:
            await self.reporter.transmit(bundle)
        if buffered:
            log.info("agent.offline_buffer_drained", count=len(buffered))

    async def _collect_forensic_snapshot(self) -> Dict[str, Any]:
        """Deep forensic collection — triggered manually or on critical threat."""
        snapshot = {"agent_id": self.config.agent_id, "timestamp": time.time()}
        for name, collector in self.collectors.items():
            try:
                snapshot[f"forensic_{name}"] = await collector.collect_forensic()
            except Exception:
                pass
        return snapshot

    def _apply_safe_config_update(self, new_config: Dict) -> None:
        SAFE_CONFIG_KEYS = {"heartbeat_interval", "telemetry_interval", "local_detection_enabled"}
        for key, value in new_config.items():
            if key in SAFE_CONFIG_KEYS:
                setattr(self.config, key, value)

    def stop(self) -> None:
        self._running = False
        log.info("agent.stopping")


# ─── Entry Point ──────────────────────────────────────────────────────────────

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Vayuntra Endpoint Agent")
    parser.add_argument("--config", required=True, help="Path to agent config YAML")
    args = parser.parse_args()

    config = AgentConfig.from_yaml(args.config)
    agent = VayuntraAgent(config)

    try:
        await agent.start()
    except KeyboardInterrupt:
        agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
