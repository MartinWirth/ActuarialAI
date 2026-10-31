"""Rolling-origin, calendar-time evaluation of one-step paid-claims predictions."""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


def rolling_backtest(triangle: pd.DataFrame, min_train_pairs: int = 8) -> pd.DataFrame:
    """At each valuation diagonal, fit only on already observable development pairs.

    Predict next-calendar-period cumulative paid for each origin with an observed
    positive paid value. Compare chain-ladder and RF on identical held-out cells.
    Excludes ages for which the training snapshot has no estimable factor.
    """
    arr = triangle.to_numpy(dtype=float)
    n, m = arr.shape
    if n != m or n < 4:
        raise ValueError("Expected a square triangle with at least four origin periods")
    results = []
    for valuation in range(2, n - 1):
        pairs = []
        for i in range(n):
            for j in range(m - 1):
                if i + j + 1 > valuation:
                    continue
                x, y = arr[i, j], arr[i, j + 1]
                if np.isfinite(x) and np.isfinite(y) and x > 0:
                    pairs.append((i, j, x, y / x))
        if len(pairs) < min_train_pairs:
            continue
        train = pd.DataFrame(pairs, columns=["origin", "development", "paid", "factor"])
        rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, random_state=42)
        rf.fit(train[["development", "paid"]], train["factor"])
        for i in range(n):
            age = valuation - i
            if age < 0 or age >= m - 1:
                continue
            if i + age + 1 != valuation + 1:
                raise AssertionError("Invalid calendar boundary")
            x, y = arr[i, age], arr[i, age + 1]
            if not (np.isfinite(x) and np.isfinite(y) and x > 0):
                continue
            peers = train[train["development"] == age]
            if peers.empty:
                continue
            classical = float(np.sum(peers["paid"] * peers["factor"]) / peers["paid"].sum())
            ml = max(1.0, float(rf.predict(pd.DataFrame([{"development": age, "paid": x}]))[0]))
            results.append({
                "valuation": valuation, "origin": triangle.index[i], "development": age,
                "actual": y, "chain_ladder": x * classical, "random_forest": x * ml,
            })
    return pd.DataFrame(results, columns=[
        "valuation", "origin", "development", "actual", "chain_ladder", "random_forest"
    ])


def backtest_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    """Comparable MAE and RMSE over the same held-out observations."""
    if predictions.empty:
        raise ValueError("No holdout observations; increase triangle size")
    rows = []
    for model in ("chain_ladder", "random_forest"):
        error = predictions[model].to_numpy() - predictions["actual"].to_numpy()
        rows.append({"model": model, "n": len(error), "MAE": float(np.mean(np.abs(error))),
                     "RMSE": float(np.sqrt(np.mean(error ** 2)))})
    return pd.DataFrame(rows).set_index("model")
