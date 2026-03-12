# ADR-001: Event-Driven Architecture for Telemetry Pipeline

**Status**: Accepted
**Date**: 2025-01-01
**Deciders**: CTO, Principal Architect, ML Lead

---

## Context

Vayuntra receives high-frequency telemetry from thousands of concurrent agent endpoints. Each agent emits process, network, filesystem, and auth events at 10-second intervals. At 1,000 agents, this is 6,000 batch payloads per minute. At 10,000 agents (national scale), this is 60,000 payloads per minute (~350MB/min of raw telemetry before compression).

We evaluated three pipeline architectures:
1. **Synchronous REST ingestion** — agent POSTs directly to backend API
2. **Event-driven (Kafka)** — agents publish to Kafka topics, consumers process asynchronously
3. **Batch file upload** — agents buffer and upload to S3, backend processes in micro-batches

---

## Decision

**Adopted: Kafka-based event-driven architecture** for all telemetry ingestion and internal event propagation.

Topics:
- `vayuntra.telemetry` — raw agent telemetry (partitioned by tenant_id)
- `vayuntra.alerts` — detected anomalies and threat events
- `vayuntra.remediation` — remediation commands and acks
- `vayuntra.audit` — immutable audit trail stream

Consumer groups:
- `ml-inference` — real-time anomaly scoring
- `behavioral-memory` — rolling baseline updates
- `alert-dispatcher` — dashboard WebSocket + email notifications
- `audit-writer` — append-only audit log persistence

---

## Consequences

**Positive:**
- Decouples ingestion rate from processing rate — handles burst loads without dropping data
- Replay capability — can reprocess historical telemetry if ML models are updated
- At-scale: Kafka handles millions of messages/sec with horizontal partition scaling
- Dead-letter queues capture malformed payloads without pipeline disruption
- Enables multi-consumer fan-out (ML + behavioral memory both consume same telemetry)

**Negative:**
- Operational complexity — Kafka cluster requires dedicated management
- Latency floor: ~100-500ms from agent emission to alert (vs ~50ms with synchronous REST)
- Adds infrastructure cost: Kafka cluster minimum 3 brokers for HA
- Agent must handle acknowledgment retry logic

**Mitigation:**
- Use managed Kafka (Confluent Cloud or Strimzi on Kubernetes) to reduce ops burden
- 100-500ms detection latency is acceptable for behavioral anomaly detection (not IPS)
- For critical local anomalies: agent performs local detection immediately, Kafka used for central correlation only

---

## Alternatives Rejected

**Synchronous REST rejected** because:
- Under burst load (attack scenario = spike in telemetry volume), API becomes the bottleneck
- No replay capability — lost telemetry if backend is temporarily unavailable
- N×1000 simultaneous HTTP connections to backend during large deployments

**S3 batch upload rejected** because:
- Minimum latency is 60-120 seconds (batch cycle), incompatible with real-time detection SLA
- Acceptable only for audit archival, not anomaly detection
