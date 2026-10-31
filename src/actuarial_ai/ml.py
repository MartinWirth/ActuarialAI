"""Development-factor regression and leakage-aware holdout evaluation.

This is an experimental benchmark, not a replacement for actuarial judgement.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from .reserving import chain_ladder


def development_samples(triangle: pd.DataFrame) -> pd.DataFrame:
    """Construct one training row per observed positive consecutive paid pair."""
    arr = triangle.to_numpy(dtype=float)
    rows = []
    for i in range(len(arr)):
        for j in range(arr.shape[1] - 1):
            current, following = arr[i, j:j + 2]
            if np.isfinite(current) and np.isfinite(following) and current > 0:
                rows.append({
                    "origin": i,
                    "development": j,
                    "paid": current,
                    "factor": following / current,
                })
    return pd.DataFrame(rows, columns=["origin", "development", "paid", "factor"])


def ml_reserving(triangle: pd.DataFrame, min_samples: int = 8) -> dict:
    """Predict development factors with RF, and extrapolate future cumulative paid.

    Uses observed development pairs only. For sparse development ages the
    classical volume-weighted factor is used as an explicit fallback.
    """
    baseline = chain_ladder(triangle)
    samples = development_samples(triangle)
    if len(samples) < min_samples:
        raise ValueError("Insufficient observed pairs to train ML model")
    model = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, random_state=42)
    features = ["development", "paid"]
    model.fit(samples[features], samples["factor"])
    arr = triangle.to_numpy(dtype=float)
    n = len(arr)
    completed = arr.copy()
    factors = baseline["factors"].to_numpy()
    counts = samples.groupby("development").size().to_dict()
    for i in range(n):
        for j in range(n - i, n):
            prev = completed[i, j - 1]
            age = j - 1
            if counts.get(age, 0) < 3:
                factor = factors[age]
            else:
                feature_row = pd.DataFrame([{"development": age, "paid": prev}])
                factor = max(1.0, float(model.predict(feature_row[features])[0]))
            completed[i, j] = prev * factor
    latest = np.array([arr[i, n - i - 1] for i in range(n)])
    summary = pd.DataFrame({
        "latest_paid": latest,
        "ultimate": completed[:, -1],
        "reserve": completed[:, -1] - latest,
    }, index=triangle.index)
    return {"summary": summary, "total_reserve": float(summary["reserve"].sum()),
            "completed": pd.DataFrame(completed, index=triangle.index, columns=triangle.columns),
            "training_pairs": len(samples)}


def holdout_last_diagonal(triangle: pd.DataFrame) -> dict:
    """Evaluate one-step-ahead predictions on a withheld latest calendar diagonal.

    Withholds the latest available cell for every origin with >=2 observed
    cells. Only earlier diagonals are used for training and forecasting.
    Report MAE on held-out cumulative claims, not on reserves.
    """
    arr = triangle.to_numpy(dtype=float)
    n = len(arr)
    masked = arr.copy()
    actual = {}
    for i in range(n - 1):
        j = n - i - 1
        actual[i] = arr[i, j]
        masked[i, j] = np.nan
    # The masked array is no longer a conventional full n-by-n triangle.
    # Compare directly at the withheld diagonal using development pairs.
    training = pd.DataFrame(masked, index=triangle.index, columns=triangle.columns)
    samples = development_samples(training)
    model = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, random_state=42)
    if len(samples) < 8:
        raise ValueError("Insufficient data for holdout evaluation")
    model.fit(samples[["development", "paid"]], samples["factor"])
    predictions = []
    for i, target in actual.items():
        j = n - i - 1
        prev = arr[i, j - 1]
        age = j - 1
        eligible = samples[samples["development"] == age]
        if len(eligible) < 3:
            if eligible.empty or eligible["paid"].sum() <= 0:
                continue
            factor = (eligible["paid"] * eligible["factor"]).sum() / eligible["paid"].sum()
        else:
            row = pd.DataFrame([{"development": age, "paid": prev}])
            factor = max(1.0, float(model.predict(row)[0]))
        predictions.append({"origin": triangle.index[i], "actual": target,
                            "predicted": prev * factor, "method": "ML with sparse-age fallback"})
    result = pd.DataFrame(predictions)
    if result.empty:
        raise ValueError("No evaluable held-out observations")
    mae = float(np.mean(np.abs(result["actual"] - result["predicted"])))
    return {"predictions": result, "mae": mae}
