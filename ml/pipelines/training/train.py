"""
Vayuntra — ML Model Training Pipeline
Trains Isolation Forest + SVM ensemble on behavioral baseline data.

Usage:
    python -m pipelines.training.train \
        --data-path /data/telemetry_features.parquet \
        --output-path /models/v1.0.0 \
        --tenant-id all

For per-tenant models:
    python -m pipelines.training.train \
        --data-path /data/telemetry_features.parquet \
        --output-path /models/tenant-abc \
        --tenant-id abc123
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import structlog
from sklearn.metrics import (
    classification_report, roc_auc_score, precision_recall_curve,
    f1_score, average_precision_score
)
from sklearn.model_selection import train_test_split

from models.anomaly.ensemble_detector import (
    IsolationForestDetector,
    SVMDetector,
    EnsembleAnomalyDetector,
    FeatureExtractor,
    TelemetryFeatures,
)

log = structlog.get_logger(__name__)


def load_dataset(data_path: str, tenant_id: Optional[str] = None) -> pd.DataFrame:
    """Load feature dataset from parquet or CSV."""
    log.info("dataset.loading", path=data_path)

    if data_path.endswith(".parquet"):
        df = pd.read_parquet(data_path)
    elif data_path.endswith(".csv"):
        df = pd.read_csv(data_path)
    else:
        raise ValueError(f"Unsupported data format: {data_path}")

    if tenant_id and tenant_id != "all":
        df = df[df["tenant_id"] == tenant_id]
        log.info("dataset.filtered", tenant_id=tenant_id, rows=len(df))

    log.info("dataset.loaded", rows=len(df), columns=len(df.columns))
    return df


def extract_feature_matrix(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """
    Extract feature matrix X and labels y from dataframe.
    
    Assumes dataset has:
    - Feature columns matching TelemetryFeatures fields
    - 'is_anomalous' column (0=normal, 1=anomaly) — for validation only
      (NOT used in unsupervised training of IF/SVM)
    """
    feature_names = list(TelemetryFeatures.__dataclass_fields__.keys())
    available_features = [f for f in feature_names if f in df.columns]
    
    if len(available_features) < len(feature_names):
        missing = set(feature_names) - set(available_features)
        log.warning("features.missing", missing=list(missing))
        # Fill missing features with 0
        for feat in missing:
            df[feat] = 0.0

    X = df[feature_names].fillna(0.0).values.astype(np.float32)
    y = df["is_anomalous"].values.astype(int) if "is_anomalous" in df.columns else np.zeros(len(df))
    
    return X, y


def train_isolation_forest(X_normal: np.ndarray, contamination: float = 0.05) -> IsolationForestDetector:
    """Train Isolation Forest on normal traffic only."""
    log.info("training.isolation_forest", samples=len(X_normal), contamination=contamination)
    
    detector = IsolationForestDetector(contamination=contamination, n_estimators=200)
    detector.fit(X_normal)
    
    return detector


def train_svm(X_normal: np.ndarray, nu: float = 0.05) -> SVMDetector:
    """Train One-Class SVM on normal traffic only."""
    log.info("training.svm", samples=len(X_normal), nu=nu)
    
    detector = SVMDetector(nu=nu)
    detector.fit(X_normal)
    
    return detector


def evaluate_model(
    detector_name: str,
    X_test: np.ndarray,
    y_test: np.ndarray,
    predict_fn,
) -> dict:
    """Evaluate a detector on test set with labeled data."""
    log.info("evaluation.running", model=detector_name, test_samples=len(X_test))
    
    predictions = []
    scores = []
    
    for x in X_test:
        is_anomalous, score = predict_fn(x)
        predictions.append(1 if is_anomalous else 0)
        scores.append(score)
    
    y_pred = np.array(predictions)
    y_scores = np.array(scores)
    
    # Only compute AUC if we have both classes in test set
    metrics = {}
    if len(np.unique(y_test)) > 1:
        metrics["roc_auc"] = round(roc_auc_score(y_test, y_scores), 4)
        metrics["avg_precision"] = round(average_precision_score(y_test, y_scores), 4)
    
    metrics["f1"] = round(f1_score(y_test, y_pred, zero_division=0), 4)
    
    # Find optimal threshold
    if len(np.unique(y_test)) > 1:
        precision, recall, thresholds = precision_recall_curve(y_test, y_scores)
        f1_scores = 2 * (precision * recall) / (precision + recall + 1e-9)
        best_threshold_idx = np.argmax(f1_scores)
        metrics["optimal_threshold"] = round(float(thresholds[best_threshold_idx]), 4)
        metrics["optimal_f1"] = round(float(f1_scores[best_threshold_idx]), 4)
    
    log.info("evaluation.results", model=detector_name, **metrics)
    return metrics


def save_model_artifacts(
    if_detector: IsolationForestDetector,
    svm_detector: SVMDetector,
    output_path: str,
    metadata: dict,
) -> None:
    """Save models and metadata to output directory."""
    out = Path(output_path)
    out.mkdir(parents=True, exist_ok=True)
    
    if_detector.save(str(out / "isolation_forest.joblib"))
    svm_detector.save(str(out / "svm.joblib"))
    
    # Write model metadata (version, metrics, training info)
    metadata["saved_at"] = datetime.utcnow().isoformat()
    metadata["artifacts"] = {
        "isolation_forest": "isolation_forest.joblib",
        "svm": "svm.joblib",
    }
    
    with open(out / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    log.info("model.saved", path=output_path)


def main():
    parser = argparse.ArgumentParser(description="Train Vayuntra anomaly detection models")
    parser.add_argument("--data-path", required=True, help="Path to feature dataset")
    parser.add_argument("--output-path", required=True, help="Output directory for model artifacts")
    parser.add_argument("--tenant-id", default="all", help="Tenant ID or 'all' for global model")
    parser.add_argument("--contamination", type=float, default=0.05, help="IF contamination parameter")
    parser.add_argument("--svm-nu", type=float, default=0.05, help="SVM nu parameter")
    parser.add_argument("--test-split", type=float, default=0.2, help="Test set fraction")
    args = parser.parse_args()

    start_time = time.time()
    log.info("training.started", tenant_id=args.tenant_id)

    # Load data
    df = load_dataset(args.data_path, args.tenant_id)
    X, y = extract_feature_matrix(df)
    
    log.info("dataset.stats", total=len(X), anomalous=int(y.sum()), normal=int((y == 0).sum()))

    # Split: use only NORMAL samples for training (unsupervised)
    # Anomalous samples used only for evaluation
    X_normal = X[y == 0]
    X_anomalous = X[y == 1]
    
    X_normal_train, X_normal_test = train_test_split(
        X_normal, test_size=args.test_split, random_state=42
    )
    
    log.info("split.complete",
             train_normal=len(X_normal_train),
             test_normal=len(X_normal_test),
             test_anomalous=len(X_anomalous))
    
    # ── Train Models ───────────────────────────────────────────────────
    if_detector = train_isolation_forest(X_normal_train, contamination=args.contamination)
    svm_detector = train_svm(X_normal_train, nu=args.svm_nu)
    
    # ── Evaluate (if labeled anomalies available) ──────────────────────
    evaluation_results = {}
    
    if len(X_anomalous) > 0:
        X_test = np.vstack([X_normal_test, X_anomalous])
        y_test = np.array([0] * len(X_normal_test) + [1] * len(X_anomalous))
        
        evaluation_results["isolation_forest"] = evaluate_model(
            "IsolationForest", X_test, y_test,
            if_detector.predict,
        )
        evaluation_results["svm"] = evaluate_model(
            "OneClassSVM", X_test, y_test,
            svm_detector.predict,
        )
    else:
        log.warning("evaluation.skipped", reason="no labeled anomalies in dataset")
    
    # ── Save Artifacts ─────────────────────────────────────────────────
    elapsed = time.time() - start_time
    
    metadata = {
        "version": f"v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "tenant_id": args.tenant_id,
        "training_samples": len(X_normal_train),
        "contamination": args.contamination,
        "svm_nu": args.svm_nu,
        "feature_count": X.shape[1],
        "evaluation": evaluation_results,
        "training_time_seconds": round(elapsed, 2),
    }
    
    save_model_artifacts(if_detector, svm_detector, args.output_path, metadata)
    
    log.info("training.complete", elapsed_seconds=round(elapsed, 2), output=args.output_path)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Training Complete — {args.tenant_id}")
    print(f"{'='*60}")
    print(f"Training samples: {len(X_normal_train):,}")
    print(f"Training time: {elapsed:.1f}s")
    if evaluation_results:
        for model, metrics in evaluation_results.items():
            print(f"\n{model}:")
            for k, v in metrics.items():
                print(f"  {k}: {v}")
    print(f"\nModels saved to: {args.output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
