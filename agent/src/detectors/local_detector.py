"""
Vayuntra Agent — Local Anomaly Detector
Lightweight Isolation Forest running on-agent for offline/sub-second detection.
Model loaded from disk (trained by control plane, distributed to agents).
Falls back to heuristic scoring when no model is present.
"""
import os
import time
from typing import Any, Dict, Tuple

import structlog

log = structlog.get_logger(__name__)


# Heuristic thresholds for model-free detection
HEURISTIC_RULES = [
    # (telemetry_path, operator, threshold, weight)
    ("processes.new_process_rate",       "gt", 30,   0.3),
    ("network.suspicious_port_hits",     "gt", 0,    0.4),
    ("network.beacon_score",             "gt", 0.7,  0.5),
    ("network.bytes_out",                "gt", 50_000_000, 0.3),  # 50MB/min
    ("filesystem.deletes_per_min",       "gt", 50,   0.4),
    ("filesystem.avg_write_entropy",     "gt", 0.8,  0.6),
    ("filesystem.exe_creates_per_min",   "gt", 5,    0.3),
    ("auth.failed_attempts",             "gt", 10,   0.3),
    ("auth.priv_escalations",            "gt", 3,    0.5),
    ("system.cpu_spike_score",           "gt", 0.9,  0.3),
]


def _get_nested(data: dict, path: str, default=0):
    """Retrieve nested value using dot-notation path."""
    parts = path.split(".")
    obj = data
    for part in parts:
        if isinstance(obj, dict):
            obj = obj.get(part, default)
        else:
            return default
    return obj if obj is not None else default


class LocalDetector:
    """
    On-agent anomaly detector.
    Primary: scikit-learn Isolation Forest loaded from .joblib model file.
    Fallback: rule-based weighted heuristic scoring.
    """

    def __init__(self, model_path: str = ""):
        self.model_path = model_path
        self._model = None
        self._scaler = None
        self.is_ready = True  # Heuristic mode is always ready
        self._model_loaded = False
        self._try_load_model()

    def _try_load_model(self):
        """Attempt to load serialized IF model from disk."""
        if not self.model_path or not os.path.exists(self.model_path):
            log.info("local_detector.no_model_file",
                     path=self.model_path or "(none)",
                     mode="heuristic_fallback")
            return

        try:
            import joblib
            bundle = joblib.load(self.model_path)
            self._model = bundle.get("model")
            self._scaler = bundle.get("scaler")
            self._model_loaded = True
            log.info("local_detector.model_loaded", path=self.model_path)
        except Exception as e:
            log.warning("local_detector.model_load_failed",
                        path=self.model_path, error=str(e))

    def detect(self, telemetry: Dict[str, Any]) -> Tuple[float, bool]:
        """
        Run anomaly detection on a telemetry snapshot.
        Returns (score: 0.0-1.0, is_anomalous: bool).
        Threshold for autonomous isolation: score > 0.90.
        """
        if self._model_loaded:
            return self._model_detect(telemetry)
        return self._heuristic_detect(telemetry)

    def _model_detect(self, telemetry: Dict[str, Any]) -> Tuple[float, bool]:
        """Use loaded Isolation Forest model."""
        try:
            import numpy as np
            vector = self._extract_vector(telemetry)
            x = np.array(vector, dtype=np.float32).reshape(1, -1)
            if self._scaler:
                x = self._scaler.transform(x)
            prediction = self._model.predict(x)[0]
            raw_score = -self._model.decision_function(x)[0]
            score = float(min(max(raw_score, 0.0), 1.0))
            is_anomalous = prediction == -1
            return score, is_anomalous
        except Exception as e:
            log.error("local_detector.model_inference_error", error=str(e))
            return self._heuristic_detect(telemetry)

    def _heuristic_detect(self, telemetry: Dict[str, Any]) -> Tuple[float, bool]:
        """
        Rule-based weighted heuristic scoring.
        Each rule contributes a weighted score; total capped at 1.0.
        """
        score = 0.0
        triggered = []

        for path, op, threshold, weight in HEURISTIC_RULES:
            value = _get_nested(telemetry, path, 0)
            hit = False
            if op == "gt":
                hit = float(value) > threshold
            elif op == "lt":
                hit = float(value) < threshold
            elif op == "eq":
                hit = value == threshold

            if hit:
                score += weight
                triggered.append(path)

        score = min(score, 1.0)
        is_anomalous = score > 0.90

        if is_anomalous:
            log.warning("local_detector.heuristic_anomaly",
                        score=round(score, 3), triggered=triggered)

        return round(score, 4), is_anomalous

    def _extract_vector(self, telemetry: Dict[str, Any]):
        """Extract the 25-feature vector matching EnsembleAnomalyDetector schema."""
        procs = telemetry.get("processes", [])
        net = telemetry.get("network", {})
        fs = telemetry.get("filesystem", {})
        auth = telemetry.get("auth", {})
        sys_t = telemetry.get("system", {})

        total_procs = len(procs)
        new_proc_rate = len([p for p in procs if p.get("age_seconds", 999) < 60])
        priv_ratio = (len([p for p in procs if p.get("elevated")]) / total_procs
                      if total_procs else 0.0)
        unsigned_ratio = (len([p for p in procs if not p.get("signed", True)]) / total_procs
                          if total_procs else 0.0)
        max_depth = max((p.get("tree_depth", 0) for p in procs), default=0)

        import time as _time
        hour = _time.localtime().tm_hour

        return [
            float(total_procs),
            float(new_proc_rate),
            float(priv_ratio),
            float(unsigned_ratio),
            float(max_depth),
            0.0,  # unusual_parent_child: requires parent tracking
            float(net.get("unique_dst_ips_count", 0)),
            float(net.get("bytes_out", 0)) / 60.0,
            float(net.get("bytes_in", 0)) / 60.0,
            float(net.get("dns_queries", 0)) / 60.0,
            float(net.get("port_entropy", 0.0)),
            float(net.get("beacon_score", 0.0)),
            float(net.get("new_external", 0)),
            float(fs.get("writes_per_min", 0)),
            float(fs.get("deletes_per_min", 0)),
            float(fs.get("exe_creates_per_min", 0)),
            float(fs.get("sensitive_access_score", 0.0)),
            float(fs.get("avg_write_entropy", 0.0)),
            float(hour) / 24.0,
            float(auth.get("failed_attempts", 0)),
            float(auth.get("priv_escalations", 0)),
            0.0,  # lateral_movement_score: computed at control plane
            float(sys_t.get("cpu_spike_score", 0.0)),
            float(sys_t.get("memory_anomaly_score", 0.0)),
            float(sys_t.get("kernel_module_loads", 0)),
        ]
