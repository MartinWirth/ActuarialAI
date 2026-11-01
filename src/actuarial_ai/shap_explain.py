"""Optional SHAP TreeExplainer diagnostics for the experimental factor model."""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from .ml import development_samples

FEATURES = ["development", "paid"]


def shap_factor_explanations(triangle: pd.DataFrame, max_rows: int = 100) -> dict:
    """Explain fitted RF factor predictions on observed training pairs.

    SHAP values are expressed in age-to-age factor units. In-sample explanations
    are descriptive, not out-of-time evidence or causal attributions.
    """
    if max_rows < 1:
        raise ValueError("max_rows must be positive")
    try:
        import shap
    except ImportError as exc:
        raise ImportError("Install optional SHAP support: pip install -e '.[explain]'") from exc
    samples = development_samples(triangle)
    if len(samples) < 8:
        raise ValueError("Insufficient observed development pairs")
    x = samples[FEATURES].iloc[:max_rows].copy()
    model = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, random_state=42)
    model.fit(samples[FEATURES], samples["factor"])
    explanation = shap.TreeExplainer(model)(x)
    values = np.asarray(explanation.values, dtype=float)
    if values.shape != (len(x), len(FEATURES)):
        raise ValueError("Unexpected SHAP shape for single-output regression")
    baseline = np.broadcast_to(np.asarray(explanation.base_values, dtype=float), (len(x),))
    predictions = model.predict(x)
    if not np.allclose(baseline + values.sum(axis=1), predictions, rtol=1e-4, atol=1e-5):
        raise ValueError("SHAP additivity check failed")
    details = x.reset_index(drop=True).copy()
    details["prediction"] = predictions
    details["baseline"] = baseline
    for i, name in enumerate(FEATURES):
        details[f"shap_{name}"] = values[:, i]
    importance = pd.DataFrame({
        "feature": FEATURES,
        "mean_absolute_shap": np.mean(np.abs(values), axis=0),
    }).sort_values("mean_absolute_shap", ascending=False).reset_index(drop=True)
    return {"details": details, "importance": importance, "n_training": len(samples)}
