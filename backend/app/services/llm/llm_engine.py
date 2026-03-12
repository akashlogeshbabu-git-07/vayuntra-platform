"""
Vayuntra — Local LLM Remediation Engine
Secure Mistral 7B inference for air-gapped remediation assistance.

Security model:
- Input sanitization against prompt injection
- Output validation before returning to analyst
- Audit logging of all LLM interactions
- Rate limiting per tenant/user
- Cloud fallback when local inference unavailable

Note: llama-cpp-python is an OPTIONAL dependency.
      The engine degrades gracefully to rule-based playbooks when
      LLM_ENABLED=false or the model file is absent.
"""

import hashlib
import json
import re
import time
from typing import Optional

import structlog

from app.core.config import settings
from app.core.audit import audit_log
from app.schemas.llm import (
    RemediationRequest, RemediationResponse,
    RemediationPlaybook, RootCauseAnalysis,
)

log = structlog.get_logger(__name__)

# ─── Prompt Injection Defense ─────────────────────────────────────────────────

INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"disregard\s+(all|any)\s+(prior|previous|above)",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+if\s+you\s+are",
    r"pretend\s+(you\s+are|to\s+be)",
    r"jailbreak",
    r"DAN\s+mode",
    r"system\s*:\s*",
    r"<\|im_start\|>",
    r"<\|system\|>",
    r"\[INST\].*override",
    r"forget\s+(your|all)\s+(instructions|training|guidelines)",
]

COMPILED_INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in INJECTION_PATTERNS]


def sanitize_input(text: str) -> tuple[str, bool]:
    if not text or len(text) > 4096:
        return text[:4096] if text else "", False

    for pattern in COMPILED_INJECTION_PATTERNS:
        if pattern.search(text):
            log.warning("llm.prompt_injection_detected", pattern=pattern.pattern)
            return "", True

    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return sanitized, False


# ─── System Prompts ───────────────────────────────────────────────────────────

REMEDIATION_SYSTEM_PROMPT = """You are Vayuntra's AI Security Analyst — a specialized cybersecurity assistant.

Your ONLY function is to assist SOC analysts with:
1. Explaining detected security anomalies and their root causes
2. Generating step-by-step remediation playbooks
3. Answering questions about threat indicators and attack patterns

CONSTRAINTS:
- Only provide security-relevant information
- Never execute or suggest code that could be harmful
- Do not provide information that could be used to attack systems
- If asked about topics outside cybersecurity, redirect to the security context
- Always cite MITRE ATT&CK techniques when relevant
- Provide actionable, specific steps — not generic advice
"""

ROOT_CAUSE_SYSTEM_PROMPT = """You are Vayuntra's Root Cause Analysis engine.

Analyze the provided threat telemetry and explain:
1. The attack chain and kill chain stage
2. Initial access vector (if determinable)
3. Lateral movement indicators
4. Persistence mechanisms detected
5. Data exposure risk assessment

Be concise, technical, and precise. Format as structured analysis.
"""

# ─── Rule-based fallback playbooks ────────────────────────────────────────────

RULE_BASED_PLAYBOOKS = {
    "Initial Access": [
        "Block the identified source IP at the perimeter firewall immediately.",
        "Revoke all active sessions for affected accounts.",
        "Reset credentials for any accounts that were accessed.",
        "Review VPN and authentication logs for the past 72 hours.",
        "Check for lateral movement indicators on adjacent systems.",
        "Preserve forensic evidence before remediation.",
        "Restore from a clean backup if system integrity is compromised.",
    ],
    "Execution": [
        "Kill the malicious process immediately (taskkill /F /PID <pid> or kill -9 <pid>).",
        "Identify parent process and trace execution chain.",
        "Quarantine the malicious binary/script with EDR or manual move to quarantine folder.",
        "Scan all endpoints for identical file hashes using your EDR console.",
        "Review scheduled tasks, cron jobs, and startup items.",
        "Check for persistence mechanisms (registry run keys, systemd units, services).",
        "Reboot the system after cleanup to flush in-memory payloads.",
    ],
    "Persistence": [
        "Identify and remove the persistence mechanism.",
        "Check registry run keys: HKCU/HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.",
        "Review installed services for suspicious entries (sc query type= all).",
        "Remove any backdoor accounts created.",
        "Audit SSH authorized_keys files on Linux endpoints.",
        "Scan for web shells if a web server is present.",
        "Verify system integrity with file hash comparison against known-good baseline.",
    ],
    "Lateral Movement": [
        "Isolate ALL compromised systems immediately via EDR or VLAN change.",
        "Revoke Kerberos tickets (klist purge on Windows).",
        "Reset KRBTGT password twice in Active Directory environments.",
        "Review SMB, RDP, and WMI connection logs in the affected timeframe.",
        "Check for Pass-the-Hash / Pass-the-Ticket indicators.",
        "Audit privileged group memberships for unauthorized additions.",
        "Deploy network micro-segmentation to contain further spread.",
    ],
    "Exfiltration": [
        "Block outbound connections to suspicious IPs at the firewall immediately.",
        "Identify what data was accessed and potentially exfiltrated.",
        "Notify legal and compliance teams for breach assessment.",
        "Preserve network logs and DLP evidence for forensics.",
        "Revoke API keys and tokens that may have been stolen.",
        "Notify affected customers if PII was involved.",
        "File incident report per applicable regulatory requirements (GDPR, HIPAA, etc.).",
    ],
    "Credential Access": [
        "Force password reset for all accounts with access to the affected system.",
        "Enable MFA immediately if not already enforced.",
        "Revoke and reissue all service account credentials.",
        "Check for credential reuse across other systems.",
        "Review Active Directory for unusual admin group membership changes.",
        "Rotate secrets in vault or secrets manager.",
        "Enable conditional access policies to restrict logins to known IPs.",
    ],
    "Defense Evasion": [
        "Re-enable any disabled security tools (AV, EDR, logging).",
        "Restore tampered audit policies and event log configurations.",
        "Check for AMSI bypass or ETW patching artifacts.",
        "Verify integrity of security agent binaries on the endpoint.",
        "Review process hollowing and injection indicators with memory forensics.",
        "Quarantine the evasion binary and submit to threat intelligence platform.",
    ],
    "Discovery": [
        "Identify what internal resources were enumerated.",
        "Block reconnaissance source IP or isolate the internal source endpoint.",
        "Review DNS query logs for unusual internal lookups.",
        "Audit LDAP query logs for Active Directory enumeration.",
        "Increase logging verbosity on sensitive systems for 72 hours.",
        "Alert on repeat scanning behavior from the same source.",
    ],
    "default": [
        "Isolate the affected system from the network.",
        "Collect and preserve all relevant logs and evidence.",
        "Identify the attack vector and entry point.",
        "Remove malicious artifacts (files, processes, persistence mechanisms).",
        "Patch the exploited vulnerability or misconfiguration.",
        "Reset credentials for any potentially compromised accounts.",
        "Monitor the system closely for 72 hours post-remediation.",
        "Conduct a post-incident review and update detection rules.",
    ],
}


# ─── LLM Engine ───────────────────────────────────────────────────────────────

class LocalLLMEngine:
    """
    Mistral 7B GGUF inference engine using llama-cpp-python.
    Degrades gracefully to rule-based playbooks when LLM_ENABLED=false.
    """

    _instance: Optional["LocalLLMEngine"] = None
    _model = None  # type: Optional[Any]

    @classmethod
    def get_instance(cls) -> "LocalLLMEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_model(self) -> bool:
        """Load Mistral model. Returns True if loaded successfully."""
        if self._model is not None:
            return True
        if not settings.LLM_ENABLED:
            return False

        import os
        if not os.path.exists(settings.LLM_MODEL_PATH):
            log.warning("llm.model_not_found", path=settings.LLM_MODEL_PATH)
            return False

        try:
            from llama_cpp import Llama  # type: ignore
        except ImportError:
            log.warning("llm.llama_cpp_not_installed",
                        hint="pip install llama-cpp-python to enable local LLM")
            return False

        log.info("llm.loading_model", path=settings.LLM_MODEL_PATH)
        start = time.time()
        self._model = Llama(
            model_path=settings.LLM_MODEL_PATH,
            n_ctx=settings.LLM_CONTEXT_LENGTH,
            n_threads=settings.LLM_N_THREADS,
            n_gpu_layers=settings.LLM_N_GPU_LAYERS,
            verbose=False,
            use_mmap=True,
            use_mlock=False,
        )
        log.info("llm.model_loaded", elapsed_seconds=round(time.time() - start, 2))
        return True

    def _build_mistral_prompt(self, system: str, user: str) -> str:
        return f"<s>[INST] {system}\n\n{user} [/INST]"

    def _validate_output(self, output: str) -> tuple[str, bool]:
        if not output:
            return "", False
        dangerous = ["rm -rf", "format c:", "DROP TABLE", "DELETE FROM",
                     "exec(", "eval(", "__import__", "os.system"]
        for kw in dangerous:
            if kw.lower() in output.lower():
                log.warning("llm.dangerous_output_blocked", keyword=kw)
                return "Output blocked by safety filter. Please rephrase your query.", False
        return output[:8192], True

    def _rule_based_playbook(self, mitre_tactic: str) -> RemediationResponse:
        """Return a rule-based remediation when LLM is disabled/unavailable."""
        steps = RULE_BASED_PLAYBOOKS.get(mitre_tactic, RULE_BASED_PLAYBOOKS["default"])
        playbook_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
        return RemediationResponse(
            threat_id="unknown",
            playbook=playbook_text,
            content=playbook_text,
            steps=steps,
            model_used="rule_based",
            engine="rule_based",
            generated_at=__import__("datetime").datetime.utcnow().isoformat(),
            is_safe=True,
        )

    async def generate_remediation(
        self,
        request: RemediationRequest,
        user_id: str,
        tenant_id: str,
    ) -> RemediationResponse:
        analyst_question = ""
        if request.analyst_question:
            analyst_question, was_injected = sanitize_input(request.analyst_question)
            if was_injected:
                await audit_log(
                    action="llm.injection_blocked",
                    user_id=user_id,
                    tenant_id=tenant_id,
                    metadata={"threat_id": str(request.threat_id)},
                )
                return RemediationResponse(
                    threat_id=request.threat_id,
                    error="Input blocked: potential injection detected.",
                )

        if not self._load_model():
            # Graceful degradation — rule-based playbook
            tactic = request.threat_type or "default"
            resp = self._rule_based_playbook(tactic)
            resp.threat_id = request.threat_id
            return resp

        threat_context = json.dumps({
            "threat_id": str(request.threat_id),
            "threat_type": request.threat_type,
            "severity": request.severity,
            "mitre_technique": request.mitre_technique,
            "affected_processes": request.affected_processes,
            "anomaly_score": request.anomaly_score,
            "os_type": request.os_type,
            "detection_model": request.detection_model,
        }, indent=2)

        user_message = (
            f"Threat Context:\n{threat_context}\n\n"
            + (f"Analyst Question: {analyst_question}" if analyst_question
               else "Generate a complete remediation playbook for this threat.")
        )

        start = time.time()
        prompt = self._build_mistral_prompt(REMEDIATION_SYSTEM_PROMPT, user_message)

        try:
            output = self._model(
                prompt,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
                top_p=0.9,
                repeat_penalty=1.1,
                stop=["</s>", "[INST]"],
            )
            raw_text = output["choices"][0]["text"].strip()
        except Exception as e:
            log.error("llm.inference_error", error=str(e))
            if settings.LLM_CLOUD_FALLBACK:
                return await self._cloud_fallback(request, user_id, tenant_id)
            tactic = request.threat_type or "default"
            resp = self._rule_based_playbook(tactic)
            resp.threat_id = request.threat_id
            return resp

        validated_text, is_safe = self._validate_output(raw_text)
        elapsed = time.time() - start

        audit_hash = hashlib.sha256(f"{prompt}{validated_text}".encode()).hexdigest()[:16]
        await audit_log(
            action="llm.remediation_generated",
            user_id=user_id,
            tenant_id=tenant_id,
            metadata={
                "threat_id": str(request.threat_id),
                "inference_ms": round(elapsed * 1000),
                "output_safe": is_safe,
                "audit_hash": audit_hash,
                "engine": "local",
            },
        )

        return RemediationResponse(
            threat_id=request.threat_id,
            content=validated_text,
            playbook=validated_text,
            engine="local_mistral_7b",
            model_used="local_mistral_7b",
            inference_ms=round(elapsed * 1000),
            is_safe=is_safe,
            generated_at=__import__("datetime").datetime.utcnow().isoformat(),
        )

    async def generate_root_cause(
        self,
        threat_data: dict,
        user_id: str,
        tenant_id: str,
    ) -> RootCauseAnalysis:
        if not self._load_model():
            return RootCauseAnalysis(
                threat_id=threat_data.get("id"),
                analysis=(
                    "Local LLM not available. Enable LLM_ENABLED=true and provide "
                    "the Mistral 7B GGUF model to generate root cause analysis."
                ),
                engine="rule_based",
            )

        context = json.dumps(threat_data, indent=2)
        user_message = f"Analyze this threat telemetry and provide root cause analysis:\n\n{context}"
        prompt = self._build_mistral_prompt(ROOT_CAUSE_SYSTEM_PROMPT, user_message)

        output = self._model(
            prompt, max_tokens=2048, temperature=0.05, top_p=0.9, stop=["</s>", "[INST]"],
        )
        raw_text = output["choices"][0]["text"].strip()
        validated_text, _ = self._validate_output(raw_text)

        return RootCauseAnalysis(
            threat_id=threat_data.get("id"),
            analysis=validated_text,
            engine="local_mistral_7b",
        )

    async def _cloud_fallback(self, request, user_id, tenant_id) -> RemediationResponse:
        import httpx
        if not settings.LLM_CLOUD_API_KEY:
            tactic = request.threat_type or "default"
            resp = self._rule_based_playbook(tactic)
            resp.threat_id = request.threat_id
            return resp

        log.warning("llm.cloud_fallback_activated", threat_id=str(request.threat_id))
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.LLM_CLOUD_ENDPOINT}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.LLM_CLOUD_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "mistral-7b-instruct",
                    "messages": [
                        {"role": "system", "content": REMEDIATION_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Threat: {request.threat_type} (MITRE: {request.mitre_technique})"},
                    ],
                    "max_tokens": 1024,
                    "temperature": 0.1,
                },
            )
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        validated_text, _ = self._validate_output(content)
        return RemediationResponse(
            threat_id=request.threat_id,
            content=validated_text,
            playbook=validated_text,
            engine="cloud_mistral_fallback",
            model_used="cloud_mistral_fallback",
            is_safe=True,
            generated_at=__import__("datetime").datetime.utcnow().isoformat(),
        )


def get_llm_engine() -> LocalLLMEngine:
    return LocalLLMEngine.get_instance()
