"""
Vayuntra — ML Inference Service
Serves the ensemble anomaly detection model via FastAPI.
Used as a sidecar to the main control plane for high-throughput scoring.

Endpoints:
  POST /predict          — Score a single telemetry feature vector
  POST /predict/batch    — Score a batch of feature vectors
  GET  /health           — Liveness probe
  GET  /model/info       — Current model metadata
"""
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import structlog
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

log = structlog.get_logger(__name__)

app = FastAPI(
    title="Vayuntra ML Inference Service",
    description="Ensemble anomaly detection scoring endpoint",
    version="0.1.0",
    docs_url="/docs",
)

# ── Model registry ────────────────────────────────────────────────────────────

MODEL_DIR = os.environ.get("MODEL_DIR", "/models")
_model_cache: Dict[str, Any] = {}


def _load_model(tenant_id: str = "global"):
    """Load model bundle for a given tenant. Falls back to global model."""
    cache_key = tenant_id
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    # Try tenant-specific model first, then global
    paths_to_try = [
        Path(MODEL_DIR) / tenant_id / "ensemble.joblib",
        Path(MODEL_DIR) / "global" / "ensemble.joblib",
        Path(MODEL_DIR) / "ensemble.joblib",
    ]

    for path in paths_to_try:
        if path.exists():
            try:
                import joblib
                bundle = joblib.load(str(path))
                _model_cache[cache_key] = bundle
                log.info("inference.model_loaded",
                         tenant=tenant_id, path=str(path))
                return bundle
            except Exception as e:
                log.error("inference.model_load_error",
                          path=str(path), error=str(e))

    log.warning("inference.no_model_found",
                tenant=tenant_id,
                hint="Train a model first: python -m pipelines.training.train")
    return None


# ── Request / Response schemas ────────────────────────────────────────────────

class PredictRequest(BaseModel):
    agent_id: str
    tenant_id: str = "global"
    features: List[float]          # 25-dimensional feature vector
    metadata: Optional[Dict[str, Any]] = None


class PredictResponse(BaseModel):
    agent_id: str
    is_anomalous: bool
    anomaly_score: float           # 0.0 – 1.0
    confidence: float
    model_scores: Dict[str, float]
    inference_ms: float
    model_version: str


class BatchPredictRequest(BaseModel):
    tenant_id: str = "global"
    samples: List[PredictRequest]


class BatchPredictResponse(BaseModel):
    results: List[PredictResponse]
    total: int
    anomalies_detected: int
    batch_inference_ms: float


# ── Inference logic ───────────────────────────────────────────────────────────

def _score_features(
    features: List[float],
    bundle: Dict,
    agent_id: str,
) -> PredictResponse:
    """Run weighted ensemble scoring on a feature vector."""
    start = time.time()

    x = np.array(features, dtype=np.float32).reshape(1, -1)
    model_scores: Dict[str, float] = {}
    weights = {"isolation_forest": 0.35, "svm": 0.35, "lstm": 0.30}

    # Isolation Forest
    if "isolation_forest" in bundle:
        try:
            pipeline = bundle["isolation_forest"]
            raw = -pipeline.decision_function(x)[0]
            model_scores["isolation_forest"] = float(min(max(raw, 0.0), 1.0))
        except Exception as e:
            log.warning("inference.if_error", error=str(e))
            model_scores["isolation_forest"] = 0.0

    # One-Class SVM
    if "svm" in bundle:
        try:
            pipeline = bundle["svm"]
            raw = -pipeline.decision_function(x)[0]
            model_scores["svm"] = float(min(max(raw, 0.0), 1.0))
        except Exception as e:
            log.warning("inference.svm_error", error=str(e))
            model_scores["svm"] = 0.0

    # LSTM: skipped in inference server (requires sequence history per agent)
    model_scores["lstm"] = 0.0

    weighted_score = sum(
        weights.get(m, 0.0) * s for m, s in model_scores.items()
    )
    threshold = bundle.get("threshold", 0.75)
    is_anomalous = weighted_score >= threshold
    confidence = min(weighted_score / threshold, 1.0) if is_anomalous else weighted_score / threshold

    elapsed_ms = (time.time() - start) * 1000

    return PredictResponse(
        agent_id=agent_id,
        is_anomalous=is_anomalous,
        anomaly_score=round(weighted_score, 4),
        confidence=round(confidence, 4),
        model_scores=model_scores,
        inference_ms=round(elapsed_ms, 3),
        model_version=bundle.get("version", "unknown"),
    )


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "healthy", "service": "vayuntra-ml-inference"}


@app.get("/model/info")
async def model_info(tenant_id: str = "global"):
    bundle = _load_model(tenant_id)
    if not bundle:
        raise HTTPException(status_code=503,
                            detail="No model loaded. Train a model first.")
    return {
        "tenant_id": tenant_id,
        "model_version": bundle.get("version", "unknown"),
        "trained_at": bundle.get("trained_at", "unknown"),
        "feature_count": bundle.get("feature_count", 25),
        "threshold": bundle.get("threshold", 0.75),
        "models_available": [k for k in bundle.keys()
                             if k in ("isolation_forest", "svm", "lstm")],
    }


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """Score a single telemetry feature vector."""
    if len(request.features) != 25:
        raise HTTPException(
            status_code=422,
            detail=f"Expected 25 features, got {len(request.features)}"
        )

    bundle = _load_model(request.tenant_id)
    if not bundle:
        raise HTTPException(status_code=503, detail="Model not available")

    return _score_features(request.features, bundle, request.agent_id)


@app.post("/predict/batch", response_model=BatchPredictResponse)
async def predict_batch(request: BatchPredictRequest):
    """Score a batch of feature vectors."""
    if not request.samples:
        raise HTTPException(status_code=422, detail="Empty batch")

    bundle = _load_model(request.tenant_id)
    if not bundle:
        raise HTTPException(status_code=503, detail="Model not available")

    start = time.time()
    results = []
    for sample in request.samples:
        if len(sample.features) != 25:
            continue
        results.append(_score_features(sample.features, bundle, sample.agent_id))

    batch_ms = (time.time() - start) * 1000
    anomalies = sum(1 for r in results if r.is_anomalous)

    return BatchPredictResponse(
        results=results,
        total=len(results),
        anomalies_detected=anomalies,
        batch_inference_ms=round(batch_ms, 2),
    )


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("ML_INFERENCE_PORT", 8001))
    log.info("ml_inference_server.starting", port=port, model_dir=MODEL_DIR)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
