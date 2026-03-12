"""
Vayuntra — Anomaly Detection Pipeline
Ensemble of Isolation Forest, One-Class SVM, and LSTM for multi-layer detection.

Architecture:
- Layer 1: Isolation Forest (unsupervised, fast — first pass)
- Layer 2: One-Class SVM (boundary refinement)
- Layer 3: LSTM (temporal/sequential anomaly — process chains, lateral movement)
- Ensemble: Weighted vote with configurable thresholds
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib

log = structlog.get_logger(__name__)


# ─── Feature Schema ───────────────────────────────────────────────────────────

@dataclass
class TelemetryFeatures:
    """
    Normalized feature vector extracted from raw endpoint telemetry.
    All features are numeric for ML compatibility.
    """
    # Process features
    process_count: float = 0.0
    new_process_rate: float = 0.0
    privileged_process_ratio: float = 0.0
    unsigned_binary_ratio: float = 0.0
    process_tree_depth: float = 0.0
    unusual_parent_child: float = 0.0     # 0/1 flag

    # Network features
    unique_dst_ips: float = 0.0
    bytes_out_per_min: float = 0.0
    bytes_in_per_min: float = 0.0
    dns_query_rate: float = 0.0
    port_scan_score: float = 0.0           # entropy of dst ports
    beacon_pattern_score: float = 0.0      # regularity of outbound connections
    new_external_connections: float = 0.0

    # File system features
    file_write_rate: float = 0.0
    file_delete_rate: float = 0.0
    executable_creation_rate: float = 0.0
    sensitive_file_access_score: float = 0.0
    entropy_of_written_files: float = 0.0  # High entropy = potential encryption

    # User / auth features
    login_hour: float = 0.0               # Hour of day (normalized 0-1)
    failed_auth_attempts: float = 0.0
    privilege_escalation_events: float = 0.0
    lateral_movement_score: float = 0.0

    # System features
    cpu_spike_score: float = 0.0
    memory_anomaly_score: float = 0.0
    kernel_module_loads: float = 0.0

    def to_vector(self) -> np.ndarray:
        return np.array([
            self.process_count, self.new_process_rate, self.privileged_process_ratio,
            self.unsigned_binary_ratio, self.process_tree_depth, self.unusual_parent_child,
            self.unique_dst_ips, self.bytes_out_per_min, self.bytes_in_per_min,
            self.dns_query_rate, self.port_scan_score, self.beacon_pattern_score,
            self.new_external_connections, self.file_write_rate, self.file_delete_rate,
            self.executable_creation_rate, self.sensitive_file_access_score,
            self.entropy_of_written_files, self.login_hour, self.failed_auth_attempts,
            self.privilege_escalation_events, self.lateral_movement_score,
            self.cpu_spike_score, self.memory_anomaly_score, self.kernel_module_loads,
        ], dtype=np.float32)

    @property
    def feature_names(self) -> List[str]:
        return list(self.__dataclass_fields__.keys())


@dataclass
class DetectionResult:
    is_anomalous: bool
    anomaly_score: float          # 0.0–1.0 normalized
    confidence: float             # 0.0–1.0
    contributing_models: Dict[str, float] = field(default_factory=dict)
    top_features: List[str] = field(default_factory=list)
    detection_latency_ms: float = 0.0
    model_version: str = ""


# ─── Feature Extractor ────────────────────────────────────────────────────────

class FeatureExtractor:
    """Transforms raw telemetry JSON payloads into normalized feature vectors."""

    def extract(self, telemetry: Dict[str, Any], baseline: Optional[Dict] = None) -> TelemetryFeatures:
        """
        Extract features from a telemetry payload.
        baseline: agent's behavioral profile for relative scoring.
        """
        features = TelemetryFeatures()
        procs = telemetry.get("processes", [])
        net = telemetry.get("network", {})
        files = telemetry.get("filesystem", {})
        auth = telemetry.get("auth", {})
        sys = telemetry.get("system", {})

        # Process features
        features.process_count = float(len(procs))
        features.new_process_rate = float(len([p for p in procs if p.get("age_seconds", 999) < 60]))
        features.privileged_process_ratio = self._ratio(
            [p for p in procs if p.get("elevated")], procs
        )
        features.unsigned_binary_ratio = self._ratio(
            [p for p in procs if not p.get("signed", True)], procs
        )
        features.process_tree_depth = float(max(
            (p.get("tree_depth", 0) for p in procs), default=0
        ))

        # Network features
        dst_ips = net.get("unique_dst_ips", [])
        features.unique_dst_ips = float(len(dst_ips))
        features.bytes_out_per_min = float(net.get("bytes_out", 0)) / 60.0
        features.bytes_in_per_min = float(net.get("bytes_in", 0)) / 60.0
        features.dns_query_rate = float(net.get("dns_queries", 0)) / 60.0
        features.port_scan_score = self._port_entropy(net.get("dst_ports", []))
        features.beacon_pattern_score = float(net.get("beacon_score", 0.0))
        features.new_external_connections = float(net.get("new_external", 0))

        # File system features
        features.file_write_rate = float(files.get("writes_per_min", 0))
        features.file_delete_rate = float(files.get("deletes_per_min", 0))
        features.executable_creation_rate = float(files.get("exe_creates_per_min", 0))
        features.sensitive_file_access_score = float(files.get("sensitive_access_score", 0.0))
        features.entropy_of_written_files = float(files.get("avg_write_entropy", 0.0))

        # Auth features
        from datetime import datetime
        features.login_hour = datetime.utcnow().hour / 24.0
        features.failed_auth_attempts = float(auth.get("failed_attempts", 0))
        features.privilege_escalation_events = float(auth.get("priv_escalations", 0))

        # System features
        features.cpu_spike_score = float(sys.get("cpu_spike_score", 0.0))
        features.memory_anomaly_score = float(sys.get("memory_anomaly_score", 0.0))
        features.kernel_module_loads = float(sys.get("kernel_module_loads", 0))

        return features

    def _ratio(self, subset: list, total: list) -> float:
        if not total:
            return 0.0
        return len(subset) / len(total)

    def _port_entropy(self, ports: list) -> float:
        """Shannon entropy of destination ports — high entropy signals port scanning."""
        if not ports:
            return 0.0
        port_counts = {}
        for p in ports:
            port_counts[p] = port_counts.get(p, 0) + 1
        total = len(ports)
        entropy = -sum((c / total) * np.log2(c / total) for c in port_counts.values())
        return float(min(entropy / 10.0, 1.0))  # Normalize to 0-1


# ─── Isolation Forest Detector ────────────────────────────────────────────────

class IsolationForestDetector:
    """
    Fast first-pass anomaly detection.
    Low false negative rate, higher false positive — designed for recall.
    """

    def __init__(self, contamination: float = 0.05, n_estimators: int = 200):
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("detector", IsolationForest(
                n_estimators=n_estimators,
                contamination=contamination,
                random_state=42,
                n_jobs=-1,
                bootstrap=True,
            ))
        ])
        self.is_fitted = False
        self.version = ""

    def fit(self, X: np.ndarray) -> None:
        """Train on normal behavior baseline."""
        log.info("isolation_forest.training", samples=len(X))
        self.pipeline.fit(X)
        self.is_fitted = True
        self.version = hashlib.md5(X.tobytes()[:1024]).hexdigest()[:8]

    def predict(self, x: np.ndarray) -> Tuple[bool, float]:
        """
        Returns (is_anomalous, score).
        Isolation Forest returns -1 for anomalies, 1 for normal.
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        x_reshaped = x.reshape(1, -1)
        prediction = self.pipeline.predict(x_reshaped)[0]
        # decision_function returns negative scores for anomalies
        score = -self.pipeline.decision_function(x_reshaped)[0]
        # Normalize to 0-1
        normalized_score = float(min(max(score, 0.0), 1.0))
        return prediction == -1, normalized_score

    def save(self, path: str) -> None:
        joblib.dump(self.pipeline, path)

    @classmethod
    def load(cls, path: str) -> "IsolationForestDetector":
        instance = cls()
        instance.pipeline = joblib.load(path)
        instance.is_fitted = True
        return instance


# ─── SVM Detector ─────────────────────────────────────────────────────────────

class SVMDetector:
    """
    One-Class SVM for boundary refinement.
    Higher precision than Isolation Forest — reduces false positives.
    """

    def __init__(self, nu: float = 0.05, kernel: str = "rbf"):
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("detector", OneClassSVM(nu=nu, kernel=kernel, gamma="scale")),
        ])
        self.is_fitted = False

    def fit(self, X: np.ndarray) -> None:
        # SVM training is expensive — subsample for large datasets
        if len(X) > 50000:
            idx = np.random.choice(len(X), 50000, replace=False)
            X = X[idx]
        log.info("svm.training", samples=len(X))
        self.pipeline.fit(X)
        self.is_fitted = True

    def predict(self, x: np.ndarray) -> Tuple[bool, float]:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted.")
        x_reshaped = x.reshape(1, -1)
        prediction = self.pipeline.predict(x_reshaped)[0]
        score = -self.pipeline.decision_function(x_reshaped)[0]
        normalized_score = float(min(max(score, 0.0), 1.0))
        return prediction == -1, normalized_score

    def save(self, path: str) -> None:
        joblib.dump(self.pipeline, path)

    @classmethod
    def load(cls, path: str) -> "SVMDetector":
        instance = cls()
        instance.pipeline = joblib.load(path)
        instance.is_fitted = True
        return instance


# ─── LSTM Detector ────────────────────────────────────────────────────────────

class LSTMDetector:
    """
    LSTM-based sequence anomaly detector.
    Detects temporal patterns: lateral movement, staged attacks, beaconing.
    Uses reconstruction error as anomaly score (autoencoder variant).
    """

    SEQUENCE_LENGTH = 20  # Number of telemetry windows per sequence
    FEATURE_DIM = 25      # Must match TelemetryFeatures vector length

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.threshold = 0.05
        self.is_fitted = False

    def _build_model(self):
        """Build LSTM autoencoder architecture."""
        try:
            import tensorflow as tf
            from tensorflow.keras import layers, Model

            encoder_input = layers.Input(shape=(self.SEQUENCE_LENGTH, self.FEATURE_DIM))
            x = layers.LSTM(64, return_sequences=True)(encoder_input)
            x = layers.LSTM(32, return_sequences=False)(x)
            encoded = layers.Dense(16)(x)

            x = layers.RepeatVector(self.SEQUENCE_LENGTH)(encoded)
            x = layers.LSTM(32, return_sequences=True)(x)
            x = layers.LSTM(64, return_sequences=True)(x)
            decoded = layers.TimeDistributed(layers.Dense(self.FEATURE_DIM))(x)

            self.model = Model(encoder_input, decoded)
            self.model.compile(optimizer="adam", loss="mse")
        except ImportError:
            log.warning("lstm.tensorflow_not_available")
            self.model = None

    def fit(self, sequences: np.ndarray, epochs: int = 50, batch_size: int = 64) -> None:
        if self.model is None:
            self._build_model()
        if self.model is None:
            return

        log.info("lstm.training", sequences=len(sequences), epochs=epochs)
        self.model.fit(
            sequences, sequences,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.1,
            shuffle=True,
            verbose=0,
        )
        # Compute threshold from training reconstruction error
        reconstructed = self.model.predict(sequences, verbose=0)
        errors = np.mean(np.abs(sequences - reconstructed), axis=(1, 2))
        self.threshold = float(np.percentile(errors, 95))
        self.is_fitted = True

    def predict_sequence(self, sequence: np.ndarray) -> Tuple[bool, float]:
        """Predict on a single sequence of shape (SEQUENCE_LENGTH, FEATURE_DIM)."""
        if not self.is_fitted or self.model is None:
            return False, 0.0

        seq = sequence.reshape(1, self.SEQUENCE_LENGTH, self.FEATURE_DIM)
        reconstructed = self.model.predict(seq, verbose=0)
        error = float(np.mean(np.abs(seq - reconstructed)))
        is_anomalous = error > self.threshold
        normalized_score = min(error / (self.threshold * 2), 1.0)
        return is_anomalous, normalized_score


# ─── Ensemble Detector ────────────────────────────────────────────────────────

class EnsembleAnomalyDetector:
    """
    Three-model ensemble with weighted voting.
    
    Voting weights (tunable):
    - Isolation Forest: 0.35 (high recall, fast)
    - SVM: 0.35 (high precision, boundary-focused)
    - LSTM: 0.30 (temporal, sequence-aware)
    
    Decision rule:
    - If weighted_score >= threshold: ANOMALOUS
    - For critical infra: use lower threshold (0.60 vs default 0.75)
    """

    WEIGHTS = {
        "isolation_forest": 0.35,
        "svm": 0.35,
        "lstm": 0.30,
    }

    def __init__(self, threshold: float = 0.75):
        self.threshold = threshold
        self.if_detector = IsolationForestDetector()
        self.svm_detector = SVMDetector()
        self.lstm_detector = LSTMDetector()
        self.feature_extractor = FeatureExtractor()
        self.sequence_buffer: Dict[str, List[np.ndarray]] = {}  # agent_id -> feature history

    def detect(
        self,
        telemetry: Dict[str, Any],
        agent_id: str,
        baseline: Optional[Dict] = None,
    ) -> DetectionResult:
        """
        Run ensemble detection on a single telemetry observation.
        """
        start = time.time()

        # Feature extraction
        features = self.feature_extractor.extract(telemetry, baseline)
        x = features.to_vector()

        model_scores = {}

        # Layer 1: Isolation Forest
        if self.if_detector.is_fitted:
            if_anomalous, if_score = self.if_detector.predict(x)
            model_scores["isolation_forest"] = if_score
        else:
            model_scores["isolation_forest"] = 0.0

        # Layer 2: SVM
        if self.svm_detector.is_fitted:
            svm_anomalous, svm_score = self.svm_detector.predict(x)
            model_scores["svm"] = svm_score
        else:
            model_scores["svm"] = 0.0

        # Layer 3: LSTM (requires sequence history)
        self._update_sequence_buffer(agent_id, x)
        if (
            self.lstm_detector.is_fitted
            and len(self.sequence_buffer.get(agent_id, [])) >= self.lstm_detector.SEQUENCE_LENGTH
        ):
            sequence = np.array(self.sequence_buffer[agent_id][-self.lstm_detector.SEQUENCE_LENGTH:])
            lstm_anomalous, lstm_score = self.lstm_detector.predict_sequence(sequence)
            model_scores["lstm"] = lstm_score
        else:
            model_scores["lstm"] = 0.0

        # Weighted ensemble score
        weighted_score = sum(
            self.WEIGHTS.get(model, 0.0) * score
            for model, score in model_scores.items()
        )

        is_anomalous = weighted_score >= self.threshold
        confidence = min(weighted_score / self.threshold, 1.0) if is_anomalous else weighted_score / self.threshold

        # Top contributing features (for analyst explainability)
        top_features = self._get_top_features(x, features)

        elapsed_ms = (time.time() - start) * 1000

        return DetectionResult(
            is_anomalous=is_anomalous,
            anomaly_score=round(weighted_score, 4),
            confidence=round(confidence, 4),
            contributing_models=model_scores,
            top_features=top_features,
            detection_latency_ms=round(elapsed_ms, 2),
        )

    def _update_sequence_buffer(self, agent_id: str, features: np.ndarray) -> None:
        if agent_id not in self.sequence_buffer:
            self.sequence_buffer[agent_id] = []
        self.sequence_buffer[agent_id].append(features)
        # Keep only last 100 observations
        if len(self.sequence_buffer[agent_id]) > 100:
            self.sequence_buffer[agent_id] = self.sequence_buffer[agent_id][-100:]

    def _get_top_features(self, x: np.ndarray, features: TelemetryFeatures) -> List[str]:
        """Return feature names with highest values relative to expected range."""
        feature_names = features.feature_names
        # Simple approach: top 3 non-zero features by absolute value
        pairs = sorted(zip(feature_names, x.tolist()), key=lambda p: abs(p[1]), reverse=True)
        return [name for name, val in pairs[:3] if abs(val) > 0.1]
