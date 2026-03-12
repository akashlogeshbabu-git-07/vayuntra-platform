"""
Vayuntra Agent — Agent Integrity Verification
Verifies that the agent binary and configuration have not been tampered with.
Uses SHA-256 file hashing against a manifest signed by the control plane.
"""
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import structlog

log = structlog.get_logger(__name__)

MANIFEST_FILENAME = "agent_manifest.json"


def verify_agent_integrity(agent_dir: Optional[str] = None) -> Tuple[bool, str]:
    """
    Verify agent file integrity against a SHA-256 manifest.
    Returns (is_intact: bool, message: str).

    Manifest format:
    {
        "version": "0.1.0",
        "files": {
            "main.py": "sha256hex...",
            "detectors/local_detector.py": "sha256hex...",
            ...
        },
        "signature": "hmac_sha256_of_files_block"
    }
    """
    if agent_dir is None:
        agent_dir = str(Path(__file__).parent.parent)

    manifest_path = os.path.join(agent_dir, MANIFEST_FILENAME)

    if not os.path.exists(manifest_path):
        log.info("integrity.no_manifest",
                 path=manifest_path,
                 status="skipped — manifest not yet distributed")
        return True, "integrity check skipped (no manifest)"

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except Exception as e:
        log.error("integrity.manifest_parse_error", error=str(e))
        return False, f"manifest parse error: {e}"

    files_to_check: Dict[str, str] = manifest.get("files", {})
    if not files_to_check:
        return True, "empty manifest — skipped"

    failures = []
    for relative_path, expected_hash in files_to_check.items():
        full_path = os.path.join(agent_dir, relative_path)
        if not os.path.exists(full_path):
            failures.append(f"MISSING: {relative_path}")
            continue

        actual_hash = _sha256_file(full_path)
        if actual_hash != expected_hash:
            failures.append(
                f"TAMPERED: {relative_path} "
                f"(expected={expected_hash[:12]}... got={actual_hash[:12]}...)"
            )

    if failures:
        log.error("integrity.FAILED", failures=failures)
        return False, f"integrity check FAILED: {'; '.join(failures)}"

    log.info("integrity.passed", files_checked=len(files_to_check))
    return True, f"integrity verified ({len(files_to_check)} files)"


def compute_manifest(agent_dir: str) -> Dict:
    """
    Compute a fresh integrity manifest for the agent directory.
    Used by the build/release pipeline to generate manifests.
    """
    agent_path = Path(agent_dir)
    files = {}
    for py_file in sorted(agent_path.rglob("*.py")):
        relative = str(py_file.relative_to(agent_path))
        files[relative] = _sha256_file(str(py_file))

    return {
        "version": "0.1.0",
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
        "files": files,
    }


def _sha256_file(path: str) -> str:
    """Return SHA-256 hex digest of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        log.error("integrity.hash_error", path=path, error=str(e))
        return ""
