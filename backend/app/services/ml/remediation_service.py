"""Remediation service — LLM or rule-based playbook generation"""
import structlog
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import BackgroundTasks

from app.db.models.models import Threat, ThreatStatus

log = structlog.get_logger(__name__)

PLAYBOOK_TEMPLATES = {
    "Initial Access": """1. Immediately isolate the affected endpoint from the network
2. Revoke all active sessions for affected accounts
3. Reset credentials for any accounts that were accessed
4. Review VPN and authentication logs for the past 72 hours
5. Check for lateral movement indicators on adjacent systems
6. Preserve forensic evidence before remediation
7. Restore from a clean backup if system integrity is compromised""",

    "Execution": """1. Kill the malicious process immediately
2. Identify parent process and trace execution chain
3. Quarantine the malicious binary/script
4. Scan all systems for similar binaries using file hash
5. Review scheduled tasks, cron jobs, and startup items
6. Check for persistence mechanisms (registry, services)
7. Reboot the system after cleanup""",

    "Persistence": """1. Identify and remove persistence mechanism
2. Check registry run keys, startup folders, scheduled tasks
3. Review installed services for suspicious entries
4. Remove any backdoor accounts created
5. Audit SSH keys and authorized_keys files (Linux)
6. Scan for web shells if web server is present
7. Verify system integrity with file hash comparison""",

    "Lateral Movement": """1. Isolate ALL compromised systems immediately
2. Revoke Kerberos tickets (klist purge on Windows)
3. Reset KRBTGT password twice (AD environments)
4. Review SMB, RDP, WMI connections in the affected timeframe
5. Check for Pass-the-Hash or Pass-the-Ticket indicators
6. Audit privileged group memberships for unauthorized additions
7. Deploy network segmentation to contain spread""",

    "Exfiltration": """1. Block outbound connections to suspicious IPs immediately
2. Identify what data was accessed and exfiltrated
3. Notify legal/compliance team for breach assessment
4. Preserve network logs and DLP evidence
5. Revoke API keys and tokens that may have been stolen
6. Notify affected customers if PII was involved
7. File incident report per regulatory requirements""",

    "default": """1. Isolate the affected system from the network
2. Collect and preserve all relevant logs and evidence
3. Identify the attack vector and entry point
4. Remove malicious artifacts (files, processes, persistence)
5. Patch the exploited vulnerability
6. Reset credentials for any potentially compromised accounts
7. Monitor the system closely for 72 hours post-remediation
8. Conduct a post-incident review and update detection rules""",
}


class RemediationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def trigger_remediation(self, threat_id, tenant_id, actor: str,
                                  background_tasks: BackgroundTasks) -> dict:
        from uuid import UUID
        result = await self.db.execute(
            select(Threat).where(Threat.id == UUID(str(threat_id)), Threat.tenant_id == UUID(str(tenant_id)))
        )
        threat = result.scalar_one_or_none()
        if not threat:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Threat not found")

        tactic = threat.mitre_tactic or "default"
        playbook = PLAYBOOK_TEMPLATES.get(tactic, PLAYBOOK_TEMPLATES["default"])
        steps = [s.strip() for s in playbook.strip().split("\n") if s.strip()]

        threat.remediation_playbook = playbook
        threat.status = ThreatStatus.REMEDIATED
        await self.db.flush()

        return {
            "threat_id": str(threat_id),
            "playbook": playbook,
            "steps": steps,
            "model_used": "rule_based",
            "generated_at": datetime.utcnow().isoformat(),
        }
