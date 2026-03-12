# Vayuntra — System Architecture Document
**Version**: 0.1.0 | **Classification**: Internal — Confidential

---

## 1. Executive Vision

### Strategic Mission

Vayuntra is an autonomous AI-driven cyber defense platform purpose-built for environments where breach dwell time must be measured in seconds, not hours. The platform unifies detection, containment, and remediation under a single AI-driven control plane — replacing the reactive analyst-in-the-loop model with autonomous defense that operates at machine speed.

### Market Differentiation

| Capability | Traditional SIEM | EDR | XDR | **Vayuntra** |
|---|---|---|---|---|
| Behavioral baselining | Log-based | Agent-based | Correlated | **Persistent ML memory** |
| Response speed | Minutes–hours | Minutes | Minutes | **Seconds (autonomous)** |
| Unknown threat handling | Rule-miss | Limited | Limited | **Sandbox + LLM analysis** |
| Air-gap operation | No | Partial | No | **Full (local LLM)** |
| Remediation intelligence | Manual playbooks | Limited | Limited | **LLM-generated, contextual** |
| Edge/IoT coverage | No | No | No | **Native edge agent** |

### GRC Alignment

Vayuntra maps directly to:
- **NIST CSF 2.0**: Identify, Protect, Detect, Respond, Recover functions
- **MITRE ATT&CK v14**: Coverage mapping across all detection models
- **SOC 2 Type II**: Continuous monitoring, audit logging, access control
- **CMMC Level 2**: Incident response, audit trails, system monitoring
- **HIPAA / PCI-DSS**: Encryption at rest/transit, access logging, alerting

---

## 2. End-to-End System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ENDPOINT LAYER                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │   Windows    │  │    Linux     │  │    macOS     │  │  Edge/IoT  │  │
│  │   Agent      │  │    Agent     │  │    Agent     │  │   Agent    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │
└─────────┼─────────────────┼─────────────────┼────────────────┼─────────┘
          │                 │                 │                │
          │    mTLS WebSocket + Kafka Publish  │                │
          ▼                 ▼                 ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA PLANE                                       │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     Kafka Cluster                               │    │
│  │  Topics: telemetry | alerts | remediation | audit              │    │
│  └────────────────────────┬────────────────────────────────────────┘    │
└───────────────────────────┼─────────────────────────────────────────────┘
                            │
          ┌─────────────────┼──────────────────┐
          ▼                 ▼                  ▼
┌──────────────────┐ ┌──────────────┐ ┌────────────────────┐
│   ML Inference   │ │  Behavioral  │ │   Alert Dispatcher  │
│   Service        │ │  Memory Svc  │ │   (WebSocket + SMS) │
│  IF+SVM+LSTM     │ │  TimescaleDB │ │                    │
└────────┬─────────┘ └──────────────┘ └────────────────────┘
         │
         ▼ Anomaly → Threat
┌─────────────────────────────────────────────────────────────────────────┐
│                      CONTROL PLANE (FastAPI)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ Threat Mgmt  │  │  Isolation   │  │  Remediation │  │ LLM Engine │  │
│  │   Service    │  │   Service    │  │   Service    │  │ (Mistral)  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              PostgreSQL (Tenant/User/Threat/Audit)               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼ HTTPS/WSS
┌─────────────────────────────────────────────────────────────────────────┐
│                       SOC DASHBOARD (React)                              │
│  Real-time threats | Anomaly feed | MITRE heatmap | Agent status        │
│  Analyst investigation | Remediation controls | Audit log               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Deployment Surface Analysis

### Enterprise Workstations (Windows / Linux / macOS)
- **Feasibility**: Full capability
- **Agent privileges**: Requires local admin / root for kernel telemetry
- **Isolation mechanisms**: Network firewall rules, process kill, user session termination
- **macOS constraint**: SIP restricts kernel extension; agent uses Endpoint Security Framework (ESF)
- **Windows**: ETW (Event Tracing for Windows) for high-fidelity process/network telemetry
- **Linux**: eBPF or auditd depending on kernel version

### Raspberry Pi / Edge Micro-Devices
- **Feasibility**: Reduced sensor set, gateway mode
- **Role**: Edge SOC gateway — aggregates telemetry from OT/IoT devices upstream
- **Performance**: Isolation Forest only (no SVM, no LSTM — CPU-constrained)
- **Sync**: Local buffer → batch upload when bandwidth available
- **Hardening**: Verified boot, read-only root, signed agent binary

### Mac Mini as Edge SOC Gateway
- **Feasibility**: Full local inference (Mistral 7B viable with 16GB RAM)
- **Role**: Air-gapped SOC node — runs full control plane stack offline
- **Stack**: Docker Compose with PostgreSQL, Redis, Kafka (single-node), ML service, LLM service
- **Sync**: Periodic sync to central control plane when connectivity available (delta sync)

### Android
- **Feasibility**: Limited — MDM work profile required
- **Capability**: Network connection monitoring, app permission auditing, VPN telemetry
- **Constraint**: No kernel access, no process tree visibility outside work profile
- **Deployment**: Via MDM (Intune / Jamf / MobileIron) for enterprise-managed devices

### iOS
- **Feasibility**: Minimal — most constrained platform
- **Capability**: Network extension (NEFilterDataProvider), managed device configuration monitoring
- **Constraint**: No process visibility, no filesystem access, sandbox enforced by design
- **Deployment**: MDM-only, supervised mode for maximum telemetry

### Air-Gapped Environments
- **Feasibility**: Full with pre-configured deployment package
- **Architecture**: Docker Compose or Kubernetes (air-gapped cluster)
- **LLM**: Mistral 7B GGUF pre-bundled — no external calls
- **Sync**: Manual export/import via encrypted USB or diode-controlled transfer
- **Model updates**: Signed model bundles, verified before deployment

### ICS / OT Edge Gateways
- **Feasibility**: Passive monitoring only (network tap / SPAN port)
- **Architecture**: Agent deployed on gateway host, NOT on PLC/DCS directly
- **Protocol support**: Modbus/TCP, DNP3, EtherNet/IP traffic analysis
- **Constraint**: Zero write access to OT network — read-only observation
- **Compliance**: IEC 62443 alignment for OT environments

---

## 4. Persistent Behavioral Memory Architecture

### Storage Layer
- **Primary**: TimescaleDB (time-series extension on PostgreSQL)
  - Automatic data partitioning by time (hypertables)
  - Continuous aggregation for rolling statistics
  - Compression for data older than 30 days
- **Feature store**: Redis for real-time feature serving to ML inference
- **Archive**: S3-compatible object storage for data older than 90 days

### Behavioral Profile Design
Each agent maintains a `BehavioralProfile` record updated via streaming aggregation:
- Process execution patterns (baseline normal process trees)
- Network connection profiles (normal peers, ports, volume)
- File access patterns (sensitive path access frequency)
- Authentication patterns (normal login hours, failure rates)
- Rolling risk score (0–100, exponential moving average)

### Retention Strategy
| Data Type | Hot (Redis) | Warm (TimescaleDB) | Cold (S3) |
|---|---|---|---|
| Real-time features | 1 hour | — | — |
| Raw telemetry | — | 30 days | 1 year |
| Behavioral baselines | Current | 90 days history | 2 years |
| Anomaly events | — | Indefinite | Indefinite |
| Audit logs | — | 1 year | 7 years |

### Model Retraining from Behavioral Memory
- Trigger: 10,000 new samples OR 7-day interval OR model drift detected
- Pipeline: TimescaleDB → feature extraction → offline training → validation → registry push
- Blue/green model deployment — new model shadow-runs before promotion
- Drift detection: KL divergence on feature distributions, threshold = 0.05

---

## 5. Autonomous Proactive Defense

### Decision Tree
```
Telemetry Received
       │
       ▼
  Local Agent Detection (IF model)
       │
  ┌────┴──────────────────────────┐
  │ Score > 0.90 (Critical)       │ Score ≤ 0.90
  ▼                               ▼
Immediate Local                 Transmit to
Network Isolation               Control Plane
+ Notify Control Plane               │
                                     ▼
                            Ensemble Detection
                            (IF + SVM + LSTM)
                                     │
                     ┌───────────────┼───────────────┐
                     │ Anomalous     │               │
                     ▼               │ Not Anomalous  │
               Threat Created        ▼               │
                     │           Log + Update        │
              ┌──────┴──────┐    Behavioral          │
              │Known Threat │    Baseline            │
              │(MITRE match)│                        │
              ▼             ▼ Unknown/Zero-day       │
        Auto-remediate   Sandbox Isolation           │
        Playbook         + LLM Analysis              │
        Execution        + Analyst Alert             │
```

### Isolation Mechanisms
| Level | Mechanism | Use Case |
|---|---|---|
| Network Isolation | OS firewall rules (iptables/WFP) | Suspected lateral movement |
| Process Kill | SIGKILL / TerminateProcess | Malicious process identified |
| Container Sandbox | Docker container isolation | Unknown binary analysis |
| Full Quarantine | Network + process + user lockout | Critical/confirmed breach |

---

## 6. Security Architecture

### STRIDE Threat Model Summary
| Threat | Control |
|---|---|
| Spoofing (agent identity) | mTLS certificate per agent, hardware fingerprint |
| Tampering (telemetry) | HMAC checksum on every telemetry bundle |
| Repudiation (analyst actions) | Immutable append-only audit log |
| Information Disclosure | Tenant namespace isolation, encryption at rest |
| Denial of Service | Rate limiting, HPA auto-scaling, circuit breakers |
| Elevation of Privilege | RBAC with Zero Trust, minimal privilege service accounts |

### Encryption Architecture
- **Transit**: TLS 1.3 everywhere; mTLS for agent-to-control-plane
- **At rest**: AES-256-GCM for database (Transparent Data Encryption)
- **Secrets**: HashiCorp Vault with dynamic credentials; no static secrets in code
- **LLM inputs/outputs**: Application-layer encryption before disk persistence
- **Behavioral profiles**: Field-level encryption for PII-adjacent data

---

## 7. Phase-Based Engineering Roadmap

### Phase 0 — Foundation (Weeks 1–2)
**Deliverables**: Repository structure, CI/CD pipeline, ADR documentation, dev environment
**Kill switch**: If core team < 2 engineers, defer Phase 1

### Phase 1 — Core Anomaly Detection MVP (Weeks 3–8)
**Deliverables**: Agent (Windows/Linux), Kafka pipeline, IF+SVM detection, basic dashboard
**Success metric**: <500ms detection latency at 100 concurrent agents, >85% F1 on test dataset
**Engineering risk**: Feature extraction quality directly determines model accuracy — invest early

### Phase 2 — Automated Threat Isolation (Weeks 9–14)
**Deliverables**: Network/process isolation engine, threat timeline, automated playbook execution
**Success metric**: <5 seconds from anomaly score to network isolation command delivery
**Engineering risk**: OS-level isolation commands differ significantly per platform

### Phase 3 — Persistent Behavioral Memory (Weeks 15–20)
**Deliverables**: TimescaleDB integration, behavioral profiles, LSTM integration, retraining pipeline
**Success metric**: Baseline established within 7 days of agent deployment, false positive rate <5%
**Engineering risk**: TimescaleDB continuous aggregation configuration requires careful tuning

### Phase 4 — Local LLM Remediation (Weeks 21–28)
**Deliverables**: Mistral 7B integration, prompt injection defense, analyst chat interface, air-gap package
**Success metric**: <8 second remediation generation, 0 successful injection attacks in red team
**Engineering risk**: Mistral 7B requires 8–16GB RAM — must right-size LLM service nodes

### Phase 5 — Enterprise Compliance & Scale (Weeks 29–38)
**Deliverables**: SOC 2 audit prep, RBAC hardening, multi-tenant billing, SIEM integration (Splunk/QRadar)
**Success metric**: SOC 2 Type I certification, support 50 tenants with 1,000 agents each

### Phase 6 — National Scale (Weeks 39–52)
**Deliverables**: Multi-region deployment, government compliance (CMMC/FedRAMP path), threat intel feeds
**Success metric**: 100,000 concurrent agents, 99.95% uptime SLA, sub-second detection

---

## 8. Platform Pricing Tiers

### Free Tier
- Up to 5 agents
- Isolation Forest detection only (no LSTM)
- 7-day behavioral memory retention
- Manual remediation only (no automation)
- Community playbook library
- Email alerts only
- Dashboard: basic view, no MITRE heatmap

### ProPlus Tier ($X/agent/month)
- Up to 100 agents
- Full ensemble detection (IF + SVM + LSTM)
- 90-day behavioral memory
- Semi-automated remediation (approval required)
- Advanced analytics and MITRE heatmap
- API access
- Email + Slack + PagerDuty alerts
- Multi-user SOC dashboard with RBAC

### Pro / Enterprise Tier (Custom)
- Unlimited agents
- Full autonomous remediation
- Persistent behavioral memory (configurable retention)
- Local LLM remediation assistant
- Air-gap deployment option
- SIEM integration (Splunk, QRadar, Sentinel)
- SSO/SAML, custom RBAC policies
- Dedicated support SLA
- Compliance reporting (SOC 2, HIPAA, PCI-DSS)
- Custom ML model training on tenant data
- ICS/OT gateway agent
- Multi-tenant management console
