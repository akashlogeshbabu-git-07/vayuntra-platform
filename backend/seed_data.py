"""
Vayuntra Demo Seed Script
Run: python seed_data.py
Creates: demo tenant, admin user, 5 agents, 15 sample threats
Login: admin@vayuntra.demo / Vayuntra@123
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal
from app.core.security import hash_password
from app.db.models.models import Base, Tenant, User, Agent, Threat, UserRole, AgentOS, AgentStatus, ThreatSeverity, ThreatStatus
from datetime import datetime, timedelta
import random
import uuid


SAMPLE_THREATS = [
    ("Suspicious PowerShell Execution", ThreatSeverity.CRITICAL, "Execution",
     "T1059.001", "powershell.exe", "172.16.0.45", "185.220.101.34"),
    ("Lateral Movement via SMB", ThreatSeverity.HIGH, "Lateral Movement",
     "T1021.002", "system", "172.16.0.12", "172.16.0.45"),
    ("Credential Dumping — LSASS", ThreatSeverity.CRITICAL, "Credential Access",
     "T1003.001", "lsass.exe", "172.16.0.8", None),
    ("Unusual Outbound Data Transfer", ThreatSeverity.HIGH, "Exfiltration",
     "T1041", "chrome.exe", "172.16.0.22", "103.21.244.0"),
    ("Persistence via Registry Run Key", ThreatSeverity.MEDIUM, "Persistence",
     "T1547.001", "reg.exe", "172.16.0.15", None),
    ("Port Scan Detected", ThreatSeverity.MEDIUM, "Discovery",
     "T1046", "nmap", "192.168.1.5", "172.16.0.0"),
    ("Ransomware File Encryption Pattern", ThreatSeverity.CRITICAL, "Impact",
     "T1486", "unknown.exe", "172.16.0.33", None),
    ("Phishing Email — Malicious Link", ThreatSeverity.HIGH, "Initial Access",
     "T1566.002", "outlook.exe", "172.16.0.9", "45.33.32.156"),
    ("Suspicious Scheduled Task", ThreatSeverity.MEDIUM, "Persistence",
     "T1053.005", "schtasks.exe", "172.16.0.17", None),
    ("DNS Tunneling Detected", ThreatSeverity.HIGH, "Exfiltration",
     "T1048.001", "dns.exe", "172.16.0.44", "8.8.8.8"),
    ("Anomalous Login — Off Hours", ThreatSeverity.MEDIUM, "Initial Access",
     "T1078", "winlogon.exe", "172.16.0.3", "41.79.79.79"),
    ("Process Injection Detected", ThreatSeverity.HIGH, "Defense Evasion",
     "T1055", "svchost.exe", "172.16.0.11", None),
    ("Brute Force SSH Attempt", ThreatSeverity.MEDIUM, "Credential Access",
     "T1110.001", "sshd", "10.0.0.1", "185.180.143.49"),
    ("Rootkit Behavior Detected", ThreatSeverity.CRITICAL, "Defense Evasion",
     "T1014", "kernel", "172.16.0.28", None),
    ("Mimikatz Usage Pattern", ThreatSeverity.CRITICAL, "Credential Access",
     "T1003", "mimikatz.exe", "172.16.0.6", None),
]

SAMPLE_AGENTS = [
    ("WIN-DC01", "172.16.0.1", AgentOS.WINDOWS, "Windows Server 2022"),
    ("WIN-WS042", "172.16.0.42", AgentOS.WINDOWS, "Windows 11 Pro"),
    ("UBUNTU-SRV01", "172.16.0.10", AgentOS.LINUX, "Ubuntu 22.04 LTS"),
    ("MACBOOK-DEV03", "172.16.0.55", AgentOS.MACOS, "macOS 14.4"),
    ("KALI-SEC01", "172.16.0.99", AgentOS.LINUX, "Kali Linux 2024.1"),
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Tenant
        from sqlalchemy import select
        result = await db.execute(select(Tenant).where(Tenant.slug == "vayuntra-demo"))
        tenant = result.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(name="Vayuntra Demo Corp", slug="vayuntra-demo", max_agents=50)
            db.add(tenant)
            await db.flush()
            print(f"✅ Tenant created: {tenant.name}")

        # Admin user
        result = await db.execute(select(User).where(User.email == "admin@vayuntra.demo"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                tenant_id=tenant.id,
                email="admin@vayuntra.demo",
                hashed_password=hash_password("Vayuntra@123"),
                full_name="Vayuntra Admin",
                role=UserRole.TENANT_ADMIN,
            )
            db.add(user)
            await db.flush()
            print(f"✅ User created: admin@vayuntra.demo / Vayuntra@123")

        # Agents
        agents = []
        for hostname, ip, os_type, os_ver in SAMPLE_AGENTS:
            result = await db.execute(select(Agent).where(Agent.hostname == hostname, Agent.tenant_id == tenant.id))
            agent = result.scalar_one_or_none()
            if not agent:
                agent = Agent(
                    tenant_id=tenant.id,
                    hostname=hostname,
                    ip_address=ip,
                    os=os_type,
                    os_version=os_ver,
                    status=AgentStatus.ONLINE if hostname != "KALI-SEC01" else AgentStatus.ISOLATED,
                    last_seen=datetime.utcnow() - timedelta(minutes=random.randint(1, 30)),
                )
                db.add(agent)
                await db.flush()
            agents.append(agent)
        print(f"✅ {len(agents)} agents ready")

        # Threats
        count = 0
        for i, (title, severity, tactic, technique, process, src_ip, dst_ip) in enumerate(SAMPLE_THREATS):
            days_ago = random.randint(0, 7)
            hours_ago = random.randint(0, 23)
            created = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)
            st = ThreatStatus.DETECTED if i < 8 else ThreatStatus.REMEDIATED
            agent = agents[i % len(agents)]
            threat = Threat(
                tenant_id=tenant.id,
                agent_id=agent.id,
                title=title,
                severity=severity,
                status=st,
                mitre_tactic=tactic,
                mitre_technique=technique,
                process_name=process,
                source_ip=src_ip,
                dest_ip=dst_ip,
                confidence_score=round(random.uniform(0.75, 0.99), 2),
                anomaly_score=round(random.uniform(0.75, 0.99), 2),
                description=f"Detected {tactic} activity via {process}. MITRE ATT&CK: {technique}.",
                evidence={"process": process, "score": round(random.uniform(0.75, 0.99), 2)},
            )
            # Override created_at by setting it after add
            db.add(threat)
            count += 1
        await db.commit()
        print(f"✅ {count} threats seeded")
        print("\n🚀 Seed complete!")
        print("   URL:      http://localhost:8000/api/docs")
        print("   Login:    admin@vayuntra.demo")
        print("   Password: Vayuntra@123")


if __name__ == "__main__":
    asyncio.run(seed())
