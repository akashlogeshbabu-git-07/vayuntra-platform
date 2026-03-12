# Vayuntra — Security & GRC Architecture

**Classification**: Internal — Security Sensitive
**Last Updated**: 2025-01-01

---

## 1. STRIDE Threat Model

### Control Plane API

| Threat | Vector | Mitigation | Residual Risk |
|---|---|---|---|
| **Spoofing** | API key theft, JWT forgery | Short-lived JWTs (30min), refresh rotation, MFA enforced for admin | Low |
| **Tampering** | MITM, payload modification | TLS 1.3 everywhere, HMAC checksums on telemetry | Low |
| **Repudiation** | Action denial | Immutable audit log (append-only, S3-archived with WORM) | Very Low |
| **Information Disclosure** | Tenant data cross-contamination | Row-level tenant isolation, namespace separation | Low |
| **DoS** | API flood, Kafka backpressure | Rate limiting (100 req/min/user), HPA, circuit breakers | Medium |
| **Elevation of Privilege** | JWT scope escalation | Strict RBAC, minimal service account permissions | Low |

### Agent Channel

| Threat | Vector | Mitigation |
|---|---|---|
| **Rogue agent** | Attacker deploys fake agent | mTLS certificate per agent, hardware fingerprint validation |
| **Command injection** | Malicious command to agent | Command schema validation, signed command payloads |
| **Agent tampering** | Attacker modifies agent binary | Agent binary hash verification on startup, code signing |
| **Replay attack** | Replay old telemetry bundles | Sequence number + timestamp validation, replay window: 5min |

### LLM Engine

| Threat | Vector | Mitigation |
|---|---|---|
| **Prompt injection** | Analyst crafts malicious input | Regex-based injection detection, structured threat context (not raw user input) |
| **Model poisoning** | Malicious training data | Air-gapped model source, signed model bundles, supply chain verification |
| **Data exfiltration** | LLM outputs sensitive data | Output validation, no PII in LLM context, rate limiting |
| **Adversarial input** | Crafted input to degrade detection | Input sanitization, output length caps, safety filter on outputs |

---

## 2. MITRE ATT&CK Coverage Mapping

### Detection Coverage by Tactic

| Tactic | Technique | Detection Model | Notes |
|---|---|---|---|
| Initial Access | T1190 (Exploit Public App) | IF + LSTM | Unusual process spawned by web server |
| Initial Access | T1566 (Phishing) | IF | Suspicious attachment execution pattern |
| Execution | T1059 (Command and Scripting) | IF + SVM | Unexpected shell/PowerShell from non-admin |
| Execution | T1106 (Native API) | IF | Unusual API call patterns |
| Persistence | T1547 (Boot Autostart) | IF + SVM | Registry/startup modification |
| Persistence | T1053 (Scheduled Task) | IF | Unusual task creation |
| Privilege Escalation | T1068 (Exploitation for Privilege Escalation) | LSTM | Privilege change in process tree |
| Defense Evasion | T1070 (Indicator Removal) | IF | Log deletion, timestomping |
| Defense Evasion | T1027 (Obfuscated Files) | SVM | High entropy file writes |
| Credential Access | T1003 (OS Credential Dumping) | IF + SVM | LSASS access, credential file access |
| Discovery | T1082 (System Information Discovery) | IF | Enumeration tools, unusual recon activity |
| Lateral Movement | T1021 (Remote Services) | LSTM | Sequential remote access patterns |
| Lateral Movement | T1075 (Pass the Hash) | SVM | Auth without password from new source |
| Collection | T1005 (Data from Local System) | IF | Mass file access/read patterns |
| Exfiltration | T1048 (Exfil Over Alt Protocol) | LSTM | Unusual outbound data volume |
| Exfiltration | T1041 (Exfil Over C2 Channel) | LSTM + IF | Beacon pattern + large outbound |
| Command & Control | T1071 (Application Layer Protocol) | LSTM | Beacon interval detection |
| Impact | T1486 (Data Encrypted for Impact) | IF + SVM | High entropy write rate (ransomware) |
| Impact | T1490 (Inhibit System Recovery) | IF | VSS deletion, backup modification |

---

## 3. Compliance Framework Alignment

### NIST CSF 2.0

| Function | Category | Vayuntra Capability |
|---|---|---|
| **Identify** | Asset Management | Agent inventory, hardware fingerprinting |
| **Identify** | Risk Assessment | Behavioral risk scoring per asset |
| **Protect** | Access Control | Zero-Trust RBAC, mTLS, MFA |
| **Protect** | Data Security | Encryption at rest/transit, data retention controls |
| **Detect** | Anomalies & Events | Ensemble ML detection, behavioral baselining |
| **Detect** | Continuous Monitoring | Real-time telemetry ingestion, 24/7 autonomous monitoring |
| **Respond** | Response Planning | Automated playbooks, analyst workflows |
| **Respond** | Mitigation | Network isolation, process containment |
| **Recover** | Recovery Planning | Remediation playbooks, system restoration guidance |

### SOC 2 Type II Controls

| Trust Service Criteria | Control | Implementation |
|---|---|---|
| CC6.1 (Access Control) | Least privilege access | RBAC, per-role endpoint restrictions |
| CC6.2 (Authentication) | MFA required for admin | TOTP, session management |
| CC6.3 (Authorization) | Role-based | 5 roles: Super Admin, Tenant Admin, SOC Analyst, Read Only, Agent Service |
| CC7.1 (System Operations) | Monitoring | Prometheus, Grafana, alerting |
| CC7.2 (Anomaly Detection) | Continuous | ML-based anomaly detection in platform |
| CC9.1 (Risk Mitigation) | Vendor assessment | Supply chain security, SBOM |

### PCI-DSS v4 Relevant Controls

- **Req 10**: Audit logging (immutable AuditLog model, 7-year retention path)
- **Req 11.4**: Intrusion detection (core platform function)
- **Req 11.5**: File integrity monitoring (filesystem collector)
- **Req 12.10**: Incident response plan (automated playbooks)

### HIPAA Technical Safeguards

- **Access Control** (§164.312(a)): RBAC, MFA, session timeouts
- **Audit Controls** (§164.312(b)): Immutable audit log
- **Integrity** (§164.312(c)): Data checksums, encryption
- **Transmission Security** (§164.312(e)): TLS 1.3 enforced

---

## 4. Encryption Architecture

### Key Hierarchy

```
Root CA (HSM-protected)
├── Intermediate CA
│   ├── Agent Certificate (per-agent, 1-year validity)
│   ├── Service Certificate (per-service, 90-day auto-rotate)
│   └── Client Certificate (analyst browser mTLS, optional)
└── TLS Wildcard Certificate (*.vayuntra.io, 90-day via cert-manager)

Application Keys (Vault-managed)
├── Database Encryption Key (AES-256-GCM)
├── JWT Signing Key (HMAC-SHA256, 30-day rotation)
├── Telemetry HMAC Key (per-tenant, HMAC-SHA256)
└── Offline Buffer Key (derived from agent shared secret)
```

### Encryption Standards

| Layer | Algorithm | Key Length | Notes |
|---|---|---|---|
| TLS | TLS 1.3 | N/A | ECDHE + AES-256-GCM |
| Database at rest | AES-256-GCM | 256-bit | Transparent Data Encryption |
| File/backup | AES-256-GCM | 256-bit | MinIO server-side encryption |
| JWT | HMAC-SHA256 | 256-bit | Short-lived, rotating |
| Agent telemetry | HMAC-SHA256 | 256-bit | Integrity, not confidentiality |
| Offline buffer | AES-256 via Fernet | 256-bit | Derived from shared secret |

---

## 5. Secrets Management

### HashiCorp Vault Integration

- All application secrets (DB passwords, API keys, JWT secrets) stored in Vault
- Dynamic credentials: PostgreSQL credentials rotated every 1 hour
- Kubernetes auth backend: pods authenticate via service account JWT
- AppRole for CI/CD pipeline secret access
- Audit logging on all Vault operations

### Secret Categories

| Secret | Storage | Rotation |
|---|---|---|
| DB passwords | Vault dynamic secrets | 1 hour |
| JWT signing key | Vault KV v2 | 30 days |
| Agent shared secret | Vault KV v2 | 90 days |
| LLM API key | Vault KV v2 | 30 days |
| TLS certificates | cert-manager + Vault PKI | 90 days auto |
| Agent mTLS certs | Vault PKI | 1 year |

---

## 6. Supply Chain Security

### SBOM (Software Bill of Materials)

- Generated on every build via Syft
- Stored as SPDX JSON artifact in CI pipeline
- Scanned against CVE database via Grype
- CRITICAL CVEs block deployment pipeline

### Container Security

- Base images: Python 3.11-slim, Node 20-alpine only
- No untrusted base images
- All images scanned with Trivy before push (CRITICAL/HIGH block)
- Distroless targets for production (roadmap)
- Non-root user enforced in all Dockerfiles
- Read-only root filesystem where possible

### Dependency Management

- Backend: pip-audit on every CI run
- Frontend: npm audit on every CI run  
- Renovate Bot: automated dependency update PRs with security context
- License compliance check: GPL/AGPL flagged for legal review

---

## 7. Incident Response Procedures

### Severity Classification

| Level | Criteria | SLA |
|---|---|---|
| P1 — Critical | Active breach confirmed, data exfiltration detected | 15 min response |
| P2 — High | Critical anomaly, isolation triggered | 1 hour response |
| P3 — Medium | High-severity alert, under investigation | 4 hours response |
| P4 — Low | Low/info alerts, no immediate risk | 24 hours review |

### Automated Response Playbooks

1. **Ransomware Detection** (T1486):
   - Immediate network isolation
   - Process kill of high-entropy writing processes
   - Snapshot evidence to forensic bucket
   - Alert SOC + management escalation

2. **Credential Dumping** (T1003):
   - Isolate affected endpoint
   - Force password reset for compromised accounts
   - Review lateral movement indicators
   - LLM-guided investigation

3. **C2 Beacon Detection** (T1071):
   - Block outbound to C2 IP/domain
   - Network isolation
   - Historical connection analysis
   - Threat intel lookup
