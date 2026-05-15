"""Unit tests for ML scoring service."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.ml_service import predict_risk, feature_columns


def test_predict_returns_required_keys():
    feats = {"bureau_score": 780, "utilization_rate": 0.1, "delinquency_status": 0}
    out = predict_risk(feats, current_limit=100000)
    for k in ("risk_label", "risk_score", "confidence", "contributing_factors",
              "recommended_action", "recommended_apr", "credit_line_change"):
        assert k in out
    assert out["risk_label"] in ("LOW", "MEDIUM", "HIGH")
    assert 0.0 <= out["risk_score"] <= 1.0
    assert out["recommended_action"] in ("EXPAND", "MONITOR", "RESTRICT")


def test_missing_features_zero_filled():
    out = predict_risk({}, current_limit=50000)
    assert "risk_label" in out
    assert isinstance(out["contributing_factors"], dict)


def test_shap_top5_size():
    out = predict_risk({"bureau_score": 600, "utilization_rate": 0.95}, current_limit=120000)
    assert len(out["contributing_factors"]) <= 5


def test_feature_columns_count():
    assert len(feature_columns()) == 53
