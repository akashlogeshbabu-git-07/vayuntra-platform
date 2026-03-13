"""
Vayuntra Demo Seed Script
Run: python seed_data.py
Creates: demo tenant, admin user, 5 agents, 30 domain-tagged threats

Domain Distribution:
  🏛️  GOVERNMENT & DEFENCE  (6) — #1, 4, 9, 15, 18, 25
  🏦  BANKING & FINANCE      (5) — #2, 11, 13, 19, 20
  🏥  HOSPITAL & HEALTHCARE  (4) — #3, 10, 17, 28
  💻  IT & CYBERSECURITY     (5) — #5, 6, 14, 21, 29
  🏢  ENTERPRISE & CORPORATE (6) — #7, 8, 12, 16, 23, 27
  👤  PERSONAL / INDIVIDUAL  (4) — #22, 24, 26, 30

Login: admin@vayuntra.demo / Vayuntra@123
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal
from app.core.security import hash_password
from app.db.models.models import (
    Base, Tenant, User, Agent, Threat,
    UserRole, AgentOS, AgentStatus,
    ThreatSeverity, ThreatStatus
)
from datetime import datetime, timedelta
import random


# ─── 30 DOMAIN-TAGGED THREATS ─────────────────────────────────────────────────
# Format: (title, severity, mitre_tactic, mitre_technique, process, src_ip, dst_ip, description)

SAMPLE_THREATS = [

    # ══════════════════════════════════════════════════
    # 🔴 CRITICAL — 10 THREATS
    # ══════════════════════════════════════════════════

    # #1 — 🏛️ GOVERNMENT
    (
        "[GOV] Ransomware Pre-Detonation on Ministry of Defence Server",
        ThreatSeverity.CRITICAL,
        "Impact",
        "T1486",
        "unknown.exe",
        "10.0.10.47",
        "185.220.101.34",
        "GOVERNMENT: Mass file encryption on Ministry of Defence internal server. "
        "3,000+ classified documents renamed .locked in 90 seconds. "
        "Shadow copies deleted. Matches LockBit 3.0 nation-state variant. "
        "Critical infrastructure at risk — immediate isolation required."
    ),

    # #2 — 🏦 BANKING
    (
        "[BANK] C2 Beacon on Core Banking SWIFT Payment System",
        ThreatSeverity.CRITICAL,
        "Command and Control",
        "T1071",
        "svchost.exe",
        "192.168.10.23",
        "45.33.32.156",
        "BANKING: Cobalt Strike beacon on SWIFT core banking server. "
        "Attacker C2 over port 443 — beacon every 60 seconds. "
        "Threat actor profile matches FIN7 financial crime group. "
        "Transaction systems at risk of manipulation."
    ),

    # #3 — 🏥 HOSPITAL
    (
        "[HOSPITAL] Credential Dump on Patient Records Database Server",
        ThreatSeverity.CRITICAL,
        "Credential Access",
        "T1003.001",
        "mimikatz.exe",
        "172.20.0.8",
        None,
        "HEALTHCARE: Mimikatz dump against LSASS on hospital patient records server. "
        "All domain sessions compromised including doctor and admin accounts. "
        "HIPAA violation — 50,000+ patient records exposed. "
        "Immediate domain-wide password reset required."
    ),

    # #4 — 🏛️ GOVERNMENT
    (
        "[GOV] Rootkit on Power Grid SCADA Control System",
        ThreatSeverity.CRITICAL,
        "Defense Evasion",
        "T1014",
        "kernel",
        "10.0.20.28",
        None,
        "GOVERNMENT: Unsigned kernel module on SCADA system controlling power grid substations. "
        "DKOM hiding malicious process from OS. "
        "Nation-state attack on critical national infrastructure. "
        "Power disruption to 2 million citizens possible."
    ),

    # #5 — 💻 IT COMPANY
    (
        "[IT] Log4Shell Zero-Day on DevOps CI/CD Pipeline",
        ThreatSeverity.CRITICAL,
        "Initial Access",
        "T1190",
        "java.exe",
        "45.155.205.233",
        "10.10.0.1",
        "IT COMPANY: Log4Shell CVE-2021-44228 on public-facing Jenkins server. "
        "JNDI lookup in HTTP User-Agent triggering remote class load from attacker LDAP. "
        "Build pipeline compromised — all production deployments potentially backdoored. "
        "Patch Log4j across entire infrastructure immediately."
    ),

    # #6 — 💻 IT COMPANY
    (
        "[IT] Supply Chain Attack via Malicious NPM Package in CI/CD",
        ThreatSeverity.CRITICAL,
        "Initial Access",
        "T1195.002",
        "node.exe",
        "10.10.0.55",
        "npmjs.com",
        "IT COMPANY: Trojanized NPM package exfiltrating AWS_SECRET_ACCESS_KEY and API tokens. "
        "Affects all developers who ran npm install in last 72 hours. "
        "Rotate all secrets and audit dependency tree immediately."
    ),

    # #7 — 🏢 ENTERPRISE
    (
        "[CORP] PowerShell Empire Fileless Attack on HR Management System",
        ThreatSeverity.CRITICAL,
        "Execution",
        "T1059.001",
        "powershell.exe",
        "192.168.1.45",
        "185.220.101.34",
        "ENTERPRISE: PowerShell Empire executing entirely in memory on HR server. "
        "Base64 payload via IEX — no files written to disk. AMSI bypass via reflection. "
        "Employee salary and PII data at risk — 8,000 employee records exposed."
    ),

    # #8 — 🏢 ENTERPRISE
    (
        "[CORP] Kerberoasting Attack on Corporate Active Directory",
        ThreatSeverity.CRITICAL,
        "Credential Access",
        "T1558.003",
        "rubeus.exe",
        "192.168.1.33",
        None,
        "ENTERPRISE: Rubeus requesting TGS tickets for all SPN service accounts on AD. "
        "Tickets exported for offline cracking. "
        "Targets: MSSQL_SVC, IIS_ADMIN, EXCHANGE_SVC. Full domain compromise imminent."
    ),

    # #9 — 🏛️ GOVERNMENT
    (
        "[GOV] Golden Ticket Forged on Election Commission Database",
        ThreatSeverity.CRITICAL,
        "Lateral Movement",
        "T1550.003",
        "mimikatz.exe",
        "10.0.10.6",
        None,
        "GOVERNMENT: Golden Ticket attack on Election Commission network. "
        "Forged Kerberos TGT using KRBTGT hash — 10-year ticket lifetime. "
        "Full domain access achieved. Voter registration database accessible. "
        "KRBTGT password must be reset twice immediately."
    ),

    # #10 — 🏥 HOSPITAL
    (
        "[HOSPITAL] WannaCry Worm Spreading Across ICU Network",
        ThreatSeverity.CRITICAL,
        "Lateral Movement",
        "T1210",
        "wannacry.exe",
        "172.20.0.52",
        "172.20.0.0",
        "HEALTHCARE: WannaCry exploiting EternalBlue MS17-010 across ICU network. "
        "12 medical devices encrypted including ventilator monitoring systems. "
        "Patient safety at immediate risk. Isolate all unpatched Windows medical devices."
    ),

    # ══════════════════════════════════════════════════
    # 🟠 HIGH — 10 THREATS
    # ══════════════════════════════════════════════════

    # #11 — 🏦 BANKING
    (
        "[BANK] Lateral Movement on SWIFT Interbank Payment Network",
        ThreatSeverity.HIGH,
        "Lateral Movement",
        "T1021.002",
        "system",
        "192.168.10.12",
        "192.168.10.45",
        "BANKING: Pass-the-Hash lateral movement on SWIFT payment network. "
        "Attacker moving from teller workstation toward SWIFT gateway. "
        "Estimated exposure: ₹200 crore in pending transactions."
    ),

    # #12 — 🏢 ENTERPRISE
    (
        "[CORP] 4.7GB Customer PII Database Exfiltrated to Russia",
        ThreatSeverity.HIGH,
        "Exfiltration",
        "T1041",
        "chrome.exe",
        "192.168.1.22",
        "103.21.244.0",
        "ENTERPRISE: 4.7GB customer database uploaded to Russian IP in 12 minutes. "
        "Includes Aadhaar numbers, phone numbers, and transaction history. "
        "GDPR and IT Act violation. Notify DPA within 72 hours."
    ),

    # #13 — 🏦 BANKING
    (
        "[BANK] Spearphishing Email Targeting Finance Team — Emotet Dropper",
        ThreatSeverity.HIGH,
        "Initial Access",
        "T1566.001",
        "outlook.exe",
        "192.168.10.9",
        "45.33.32.156",
        "BANKING: Spearphishing with malicious Word macro targeting bank finance team. "
        "Subject: 'RBI Compliance Audit Q1 2026 — ACTION REQUIRED'. "
        "Emotet dropper downloaded. 3 finance executives opened attachment."
    ),

    # #14 — 💻 IT COMPANY
    (
        "[IT] DLL Hollowing on Security Operations Analyst Workstation",
        ThreatSeverity.HIGH,
        "Defense Evasion",
        "T1055.012",
        "explorer.exe",
        "10.10.0.11",
        None,
        "IT COMPANY: DLL hollowing into explorer.exe on SOC analyst workstation. "
        "Reverse shell established on port 4444. "
        "Attacker has visibility into all security monitoring tools and alert feeds."
    ),

    # #15 — 🏛️ GOVERNMENT
    (
        "[GOV] DNS Tunneling Covert Channel from Intelligence Agency Network",
        ThreatSeverity.HIGH,
        "Exfiltration",
        "T1048.001",
        "dns.exe",
        "10.0.30.44",
        "8.8.8.8",
        "GOVERNMENT: DNS tunneling via Iodine on classified intelligence network. "
        "3,200 DNS queries/minute bypassing firewall DPI — exfiltrating 50KB/min. "
        "Classified documents potentially leaked. Analyst account suspended."
    ),

    # #16 — 🏢 ENTERPRISE
    (
        "[CORP] WMI Abuse Living-off-the-Land on CEO Workstation",
        ThreatSeverity.HIGH,
        "Execution",
        "T1047",
        "wmic.exe",
        "192.168.1.19",
        None,
        "ENTERPRISE: WMI event subscription on CEO workstation triggering on every startup. "
        "Fileless technique evading all installed AV. "
        "Board-level communications and M&A strategy documents at risk."
    ),

    # #17 — 🏥 HOSPITAL
    (
        "[HOSPITAL] Privilege Escalation on MRI Machine Controller",
        ThreatSeverity.HIGH,
        "Privilege Escalation",
        "T1134.001",
        "cmd.exe",
        "172.20.0.31",
        None,
        "HEALTHCARE: Token impersonation on MRI machine control workstation. "
        "PrintSpoofer escalation from nurse login to SYSTEM confirmed. "
        "Patient scan data and device firmware at risk of manipulation."
    ),

    # #18 — 🏛️ GOVERNMENT
    (
        "[GOV] Cobalt Strike Moving to Defence Ministry Domain Controller",
        ThreatSeverity.HIGH,
        "Lateral Movement",
        "T1569.002",
        "psexec.exe",
        "10.0.10.23",
        "10.0.10.1",
        "GOVERNMENT: Cobalt Strike PSEXEC lateral movement to Defence Ministry DC. "
        "Service binary dropped to ADMIN$ share and executed remotely. "
        "Full ministry network compromise imminent."
    ),

    # #19 — 🏦 BANKING
    (
        "[BANK] 14,000 Credential Stuffing Attempts on Online Banking Portal",
        ThreatSeverity.HIGH,
        "Credential Access",
        "T1110.004",
        "python.exe",
        "91.108.4.0",
        "192.168.10.1",
        "BANKING: 14,000 automated login attempts against online banking portal. "
        "3 high-value accounts compromised — MFA not enforced. "
        "Estimated fraud exposure: ₹85 lakh. Block IPs and enforce MFA immediately."
    ),

    # #20 — 🏦 BANKING
    (
        "[BANK] BEC CEO Impersonation — ₹47 Lakh Wire Transfer Fraud",
        ThreatSeverity.HIGH,
        "Initial Access",
        "T1566.002",
        "outlook.exe",
        "192.168.10.9",
        "wire-transfer.evil.com",
        "BANKING: CEO impersonation via lookalike domain requesting ₹47 lakh wire transfer. "
        "Passed SPF/DKIM via compromised email provider. Finance manager targeted. "
        "Freeze all pending wires immediately."
    ),

    # ══════════════════════════════════════════════════
    # 🟡 MEDIUM — 10 THREATS
    # ══════════════════════════════════════════════════

    # #21 — 💻 IT COMPANY
    (
        "[IT] Internal Recon Port Scan Across Cloud Infrastructure",
        ThreatSeverity.MEDIUM,
        "Discovery",
        "T1046",
        "nmap",
        "10.10.0.5",
        "10.10.0.0",
        "IT COMPANY: Nmap SYN scan across cloud infrastructure subnet 10.10.0.0/24. "
        "All 65535 ports scanned with OS fingerprinting. "
        "Database ports 3306, 6379, 27017 probed — verify if authorized pentest."
    ),

    # #22 — 👤 PERSONAL
    (
        "[PERSONAL] SSH Brute Force — 8,400 Attempts on Home Server",
        ThreatSeverity.MEDIUM,
        "Credential Access",
        "T1110.001",
        "sshd",
        "185.180.143.49",
        "192.168.1.10",
        "PERSONAL: 8,400 failed SSH login attempts in 30 minutes from Romanian IP. "
        "Home server exposed on port 22. Fail2ban not configured. "
        "Switch to SSH key-only authentication immediately."
    ),

    # #23 — 🏢 ENTERPRISE
    (
        "[CORP] Malicious Scheduled Task Persistence on Payroll Server",
        ThreatSeverity.MEDIUM,
        "Persistence",
        "T1053.005",
        "schtasks.exe",
        "192.168.1.17",
        None,
        "ENTERPRISE: Scheduled task 'WindowsPayrollHelper' running encoded PowerShell every 5 min. "
        "Created by non-admin service account. "
        "Salary data for 8,000 staff potentially at risk."
    ),

    # #24 — 👤 PERSONAL
    (
        "[PERSONAL] Registry Run Key Persistence on Personal Laptop",
        ThreatSeverity.MEDIUM,
        "Persistence",
        "T1547.001",
        "reg.exe",
        "192.168.1.15",
        None,
        "PERSONAL: Malicious registry run key on personal Windows laptop. "
        "Key 'AdobeUpdater' pointing to svchost32.exe — not a legitimate binary. "
        "Likely installed via cracked software. Executes on every user login."
    ),

    # #25 — 🏛️ GOVERNMENT
    (
        "[GOV] Off-Hours TOR Login to Income Tax Department Portal",
        ThreatSeverity.MEDIUM,
        "Initial Access",
        "T1078",
        "winlogon.exe",
        "41.79.79.79",
        "10.0.30.3",
        "GOVERNMENT: Tax administrator logged in at 02:47 AM from TOR exit node. "
        "Never accessed outside business hours in 3-year history. MFA bypassed. "
        "2.3 lakh taxpayer records were accessible during session."
    ),

    # #26 — 👤 PERSONAL
    (
        "[PERSONAL] XMRig Cryptominer on Student Laptop — CPU 98%",
        ThreatSeverity.MEDIUM,
        "Impact",
        "T1496",
        "xmrig.exe",
        "192.168.1.38",
        "pool.minexmr.com",
        "PERSONAL: XMRig Monero miner on student laptop — CPU at 98% for 6 hours. "
        "Mining to minexmr.com:3333. Installed via pirated software. "
        "Attacker earning ₹200/day from victim electricity."
    ),

    # #27 — 🏢 ENTERPRISE
    (
        "[CORP] Insider Threat — 3.2GB Sensitive Files Copied to USB",
        ThreatSeverity.MEDIUM,
        "Exfiltration",
        "T1052.001",
        "explorer.exe",
        "192.168.1.42",
        None,
        "ENTERPRISE: 3.2GB sensitive files copied to USB outside business hours. "
        "Files include *acquisition*, *board_minutes*, *salary* documents. "
        "Employee resigned yesterday — insider threat confirmed."
    ),

    # #28 — 🏥 HOSPITAL
    (
        "[HOSPITAL] RDP Brute Force on Hospital Administration System",
        ThreatSeverity.MEDIUM,
        "Credential Access",
        "T1110.003",
        "termservice.exe",
        "194.165.16.11",
        "172.20.0.1",
        "HEALTHCARE: 5,200 RDP authentication failures in 45 minutes on hospital admin server. "
        "NLA not enforced. Attacker targeting appointment and billing systems. "
        "Block RDP from internet — enforce NLA and VPN access."
    ),

    # #29 — 💻 IT COMPANY
    (
        "[IT] Cron Reverse Shell Persistence on Production Web Server",
        ThreatSeverity.MEDIUM,
        "Persistence",
        "T1053.003",
        "cron",
        "10.10.0.10",
        "185.220.101.34",
        "IT COMPANY: Cron job executing reverse bash shell every 5 minutes to attacker IP. "
        "Added by www-data — web RCE was precursor. "
        "All customer-facing API traffic potentially intercepted."
    ),

    # #30 — 👤 PERSONAL
    (
        "[PERSONAL] Shadow IT — 14GB Corporate Files Synced to Personal Dropbox",
        ThreatSeverity.MEDIUM,
        "Exfiltration",
        "T1567.002",
        "dropbox.exe",
        "192.168.1.55",
        "dropbox.com",
        "PERSONAL: Work-from-home employee syncing 14GB corporate files to personal Dropbox. "
        "Includes source code and customer contact lists. "
        "CASB policy violation — revoke Dropbox access on corporate network."
    ),
]


SAMPLE_AGENTS = [
    ("WIN-DC01",      "172.16.0.1",  AgentOS.WINDOWS, "Windows Server 2022",  AgentStatus.ONLINE),
    ("WIN-WS042",     "172.16.0.42", AgentOS.WINDOWS, "Windows 11 Pro",       AgentStatus.ONLINE),
    ("UBUNTU-SRV01",  "172.16.0.10", AgentOS.LINUX,   "Ubuntu 22.04 LTS",     AgentStatus.ONLINE),
    ("MACBOOK-DEV03", "172.16.0.55", AgentOS.MACOS,   "macOS 14.4",           AgentStatus.ONLINE),
    ("KALI-SEC01",    "172.16.0.99", AgentOS.LINUX,   "Kali Linux 2024.1",    AgentStatus.ISOLATED),
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        # ── Tenant ──────────────────────────────────────────────────────────
        result = await db.execute(select(Tenant).where(Tenant.slug == "vayuntra-demo"))
        tenant = result.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(name="Vayuntra Demo Corp", slug="vayuntra-demo", max_agents=50)
            db.add(tenant)
            await db.flush()
            print(f"✅ Tenant created: {tenant.name}")
        else:
            print(f"✅ Tenant exists: {tenant.name}")

        # ── Admin user ───────────────────────────────────────────────────────
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
        else:
            print(f"✅ User exists: admin@vayuntra.demo")

        # ── Agents ───────────────────────────────────────────────────────────
        agents = []
        for hostname, ip, os_type, os_ver, status in SAMPLE_AGENTS:
            result = await db.execute(
                select(Agent).where(Agent.hostname == hostname, Agent.tenant_id == tenant.id)
            )
            agent = result.scalar_one_or_none()
            if not agent:
                agent = Agent(
                    tenant_id=tenant.id,
                    hostname=hostname,
                    ip_address=ip,
                    os=os_type,
                    os_version=os_ver,
                    status=status,
                    last_seen=datetime.utcnow() - timedelta(minutes=random.randint(1, 30)),
                )
                db.add(agent)
                await db.flush()
            agents.append(agent)
        print(f"✅ {len(agents)} agents ready")

        # ── Threats ──────────────────────────────────────────────────────────
        existing = await db.execute(
            select(Threat).where(Threat.tenant_id == tenant.id)
        )
        existing_titles = {t.title for t in existing.scalars().all()}

        count = 0
        for i, (title, severity, tactic, technique, process, src_ip, dst_ip, description) in enumerate(SAMPLE_THREATS):
            if title in existing_titles:
                continue

            if i < 8:
                st = ThreatStatus.DETECTED
            elif i < 12:
                st = ThreatStatus.INVESTIGATING
            elif i < 15:
                st = ThreatStatus.CONTAINED
            else:
                st = ThreatStatus.REMEDIATED

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
                description=description,
                evidence={
                    "process": process,
                    "source_ip": src_ip,
                    "technique": technique,
                    "score": round(random.uniform(0.75, 0.99), 2),
                },
            )
            db.add(threat)
            count += 1

        await db.commit()

        print(f"✅ {count} new threats seeded")
        print("\n" + "═" * 62)
        print("  🚀 Vayuntra Seed Complete!")
        print("  URL:      http://localhost:8000")
        print("  API Docs: http://localhost:8000/api/docs")
        print("  Login:    admin@vayuntra.demo")
        print("  Password: Vayuntra@123")
        print("═" * 62)
        print("\n  Domain Coverage:")
        print("  🏛️  GOVERNMENT & DEFENCE  (6) → #1, #4, #9, #15, #18, #25")
        print("  🏦  BANKING & FINANCE     (5) → #2, #11, #13, #19, #20")
        print("  🏥  HOSPITAL & HEALTHCARE (4) → #3, #10, #17, #28")
        print("  💻  IT & CYBERSECURITY    (5) → #5, #6, #14, #21, #29")
        print("  🏢  ENTERPRISE & CORP     (6) → #7, #8, #12, #16, #23, #27")
        print("  👤  PERSONAL / INDIVIDUAL (4) → #22, #24, #26, #30")
        print("═" * 62)


if __name__ == "__main__":
    asyncio.run(seed())