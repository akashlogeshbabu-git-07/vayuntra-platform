# Vayuntra — Architecture Decision Records (ADR)

This directory contains all Architecture Decision Records for the Vayuntra platform.
ADRs document significant architectural decisions: the context, the decision, and the consequences.

## Format

Each ADR follows this structure:
- **Status**: Proposed | Accepted | Deprecated | Superseded
- **Context**: The situation requiring a decision
- **Decision**: What we decided
- **Consequences**: Resulting trade-offs

## Index

| ID | Title | Status | Date |
|---|---|---|---|
| [ADR-001](ADR-001-event-driven-architecture.md) | Event-Driven Architecture for Telemetry Pipeline | Accepted | 2025-01-01 |
| [ADR-002](ADR-002-ensemble-ml-detection.md) | Ensemble ML vs Single Model for Anomaly Detection | Accepted | 2025-01-01 |
| [ADR-003](ADR-003-local-llm-mistral.md) | Mistral 7B for Air-Gapped LLM Remediation | Accepted | 2025-01-01 |
| [ADR-004](ADR-004-timescaledb-behavioral-memory.md) | TimescaleDB for Behavioral Memory Storage | Accepted | 2025-01-01 |
| [ADR-005](ADR-005-mtls-agent-auth.md) | mTLS for Agent-to-Control-Plane Authentication | Accepted | 2025-01-01 |
| [ADR-006](ADR-006-fastapi-backend.md) | FastAPI over Django/Flask for Control Plane | Accepted | 2025-01-01 |
| [ADR-007](ADR-007-kubernetes-multitenancy.md) | Namespace-based vs Cluster-based Multi-tenancy | Accepted | 2025-01-01 |
| [ADR-008](ADR-008-react-soc-dashboard.md) | React + TypeScript for SOC Dashboard | Accepted | 2025-01-01 |
