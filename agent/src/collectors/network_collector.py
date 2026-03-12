"""
Vayuntra Agent — Network Collector
Collects network connection and traffic telemetry using psutil.
"""
import math
import time
from collections import Counter
from typing import Any, Dict, List

import structlog

log = structlog.get_logger(__name__)

# Well-known C2 / suspicious port patterns
SUSPICIOUS_PORTS = {4444, 4445, 1234, 31337, 8888, 9999, 6666, 5555}
EXTERNAL_RFC1918 = [
    ("10.", True), ("172.16.", True), ("172.17.", True), ("172.18.", True),
    ("172.19.", True), ("192.168.", True), ("127.", True), ("::1", True),
]


def _is_internal(ip: str) -> bool:
    for prefix, _ in EXTERNAL_RFC1918:
        if ip.startswith(prefix):
            return True
    return False


class NetworkCollector:
    """Collects network connection telemetry from the host OS."""

    def __init__(self, os_type: str):
        self.os_type = os_type
        self._prev_bytes_sent = 0
        self._prev_bytes_recv = 0
        self._prev_time = time.time()

    def collect(self) -> Dict[str, Any]:
        """Return network telemetry snapshot."""
        try:
            import psutil
        except ImportError:
            log.warning("network_collector.psutil_missing")
            return self._empty()

        try:
            conns = psutil.net_connections(kind="inet")
            counters = psutil.net_io_counters()

            now = time.time()
            elapsed = max(now - self._prev_time, 1)

            bytes_sent_delta = max(counters.bytes_sent - self._prev_bytes_sent, 0)
            bytes_recv_delta = max(counters.bytes_recv - self._prev_bytes_recv, 0)

            self._prev_bytes_sent = counters.bytes_sent
            self._prev_bytes_recv = counters.bytes_recv
            self._prev_time = now

            established = [c for c in conns if c.status == "ESTABLISHED"]
            dst_ips = [c.raddr.ip for c in established if c.raddr]
            dst_ports = [c.raddr.port for c in established if c.raddr]
            external_ips = [ip for ip in dst_ips if not _is_internal(ip)]
            new_external = len(set(external_ips))

            beacon_score = self._beacon_score(dst_ips)
            port_entropy = self._port_entropy(dst_ports)

            return {
                "unique_dst_ips": list(set(dst_ips))[:50],
                "unique_dst_ips_count": len(set(dst_ips)),
                "dst_ports": dst_ports[:100],
                "bytes_out": bytes_sent_delta,
                "bytes_in": bytes_recv_delta,
                "dns_queries": 0,  # Populated by DNS hook if available
                "beacon_score": beacon_score,
                "new_external": new_external,
                "total_connections": len(conns),
                "established_connections": len(established),
                "suspicious_port_hits": len([p for p in dst_ports if p in SUSPICIOUS_PORTS]),
            }
        except Exception as e:
            log.error("network_collector.error", error=str(e))
            return self._empty()

    def _beacon_score(self, dst_ips: List[str]) -> float:
        """
        Heuristic beacon detection: repeated connections to same external IP
        in short window suggests C2 beaconing. Returns 0.0-1.0.
        """
        if not dst_ips:
            return 0.0
        external = [ip for ip in dst_ips if not _is_internal(ip)]
        if not external:
            return 0.0
        counts = Counter(external)
        max_repeat = max(counts.values())
        # Score: 0 for 1 connection, approaches 1.0 for many repeated hits
        return min((max_repeat - 1) / 10.0, 1.0)

    def _port_entropy(self, ports: List[int]) -> float:
        """Shannon entropy of destination ports — high = port scanning."""
        if not ports:
            return 0.0
        counts = Counter(ports)
        total = len(ports)
        entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
        return min(entropy / 10.0, 1.0)

    def _empty(self) -> Dict[str, Any]:
        return {
            "unique_dst_ips": [], "unique_dst_ips_count": 0,
            "dst_ports": [], "bytes_out": 0, "bytes_in": 0,
            "dns_queries": 0, "beacon_score": 0.0,
            "new_external": 0, "total_connections": 0,
            "established_connections": 0, "suspicious_port_hits": 0,
        }
