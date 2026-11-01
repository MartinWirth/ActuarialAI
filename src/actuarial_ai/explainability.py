"""Transparent feature importance for the experimental factor model."""
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance

from .ml import development_samples


def factor_feature_importance(triangle: pd.DataFrame) -> pd.DataFrame:
    """In-sample permutation importance; descriptive, not causal or validated."""
    samples = development_samples(triangle)
    if len(samples) < 8:
        raise ValueError("Insufficient observed pairs")
    features = ["development", "paid"]
    x = samples[features]
    y = samples["factor"]
    model = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, random_state=42)
    model.fit(x, y)
    importance = permutation_importance(model, x, y, n_repeats=5, random_state=42,
                                        scoring="neg_mean_absolute_error")
    return pd.DataFrame({
        "feature": features,
        "importance_mean": importance.importances_mean,
        "importance_std": importance.importances_std,
    }).sort_values("importance_mean", ascending=False).reset_index(drop=True)
