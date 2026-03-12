"""
Vayuntra Agent — Control Plane Reporter
Transmits telemetry bundles to the control plane via HTTPS.
Implements offline buffering and automatic retry with exponential backoff.
"""
import asyncio
import json
import time
from typing import Any, Dict, Optional

import structlog

log = structlog.get_logger(__name__)

MAX_RETRIES = 5
RETRY_BASE_DELAY = 2.0   # seconds
RETRY_MAX_DELAY = 60.0   # seconds


class ControlPlaneReporter:
    """
    Sends telemetry bundles to the Vayuntra control plane.
    Uses httpx async client with mTLS when cert paths are configured.
    Falls back to unauthenticated HTTPS in dev mode.
    """

    def __init__(self, config):
        self.config = config
        self._client = None
        self._consecutive_failures = 0
        self._last_success_time: Optional[float] = None

    async def _get_client(self):
        """Lazily initialize httpx async client with optional mTLS."""
        if self._client is not None:
            return self._client

        try:
            import httpx

            kwargs: Dict[str, Any] = {
                "timeout": httpx.Timeout(30.0),
                "verify": True,
            }

            # mTLS configuration
            if (self.config.mtls_cert_path and
                    self.config.mtls_key_path and
                    self.config.ca_cert_path):
                import ssl
                ssl_ctx = ssl.create_default_context(cafile=self.config.ca_cert_path)
                ssl_ctx.load_cert_chain(
                    certfile=self.config.mtls_cert_path,
                    keyfile=self.config.mtls_key_path,
                )
                kwargs["verify"] = ssl_ctx
                log.info("reporter.mtls_enabled")
            else:
                log.info("reporter.mtls_disabled", mode="dev")

            self._client = httpx.AsyncClient(**kwargs)
        except ImportError:
            log.warning("reporter.httpx_missing",
                        hint="pip install httpx to enable reporting")
            self._client = None

        return self._client

    async def send_bundle(self, bundle_dict: Dict[str, Any]) -> bool:
        """
        Send a telemetry bundle to the control plane.
        Returns True on success, False on failure (will be buffered by caller).
        """
        client = await self._get_client()
        if client is None:
            return False

        url = f"{self.config.control_plane_url}/api/v1/telemetry/ingest"
        headers = {
            "Content-Type": "application/json",
            "X-Agent-ID": self.config.agent_id,
            "X-Tenant-ID": self.config.tenant_id,
        }

        # JWT/shared secret auth header
        if self.config.shared_secret:
            headers["Authorization"] = f"Bearer {self.config.shared_secret}"

        payload = {"events": [bundle_dict]}

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code in (200, 201, 202):
                    self._consecutive_failures = 0
                    self._last_success_time = time.time()
                    return True
                elif response.status_code == 401:
                    log.error("reporter.auth_failed", status=response.status_code)
                    return False
                elif response.status_code >= 500:
                    log.warning("reporter.server_error",
                                status=response.status_code, attempt=attempt + 1)
                else:
                    log.warning("reporter.unexpected_status",
                                status=response.status_code)
                    return False

            except Exception as e:
                delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                log.warning("reporter.send_failed",
                             error=str(e), attempt=attempt + 1,
                             retry_in=delay)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(delay)

        self._consecutive_failures += 1
        return False

    async def send_heartbeat(self) -> bool:
        """Send lightweight heartbeat to update agent last_seen."""
        client = await self._get_client()
        if client is None:
            return False

        url = f"{self.config.control_plane_url}/api/v1/agents/{self.config.agent_id}/status"
        headers = {
            "Content-Type": "application/json",
            "X-Agent-ID": self.config.agent_id,
        }
        if self.config.shared_secret:
            headers["Authorization"] = f"Bearer {self.config.shared_secret}"

        try:
            response = await client.patch(
                url,
                params={"status": "online"},
                headers=headers,
                timeout=10.0,
            )
            return response.status_code in (200, 204)
        except Exception as e:
            log.debug("reporter.heartbeat_failed", error=str(e))
            return False

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def is_connected(self) -> bool:
        if self._last_success_time is None:
            return False
        return (time.time() - self._last_success_time) < 120  # 2 min window
