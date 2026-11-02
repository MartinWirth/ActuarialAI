"""Import and validate cumulative paid-claims triangles from CSV or Excel."""
from io import BytesIO

import numpy as np
import pandas as pd


def validate_triangle(triangle: pd.DataFrame, *, allow_decrease: bool = False) -> pd.DataFrame:
    """Return a numeric, strictly shaped triangle suitable for chain-ladder."""
    if not isinstance(triangle, pd.DataFrame):
        raise TypeError("Expected a DataFrame")
    n, m = triangle.shape
    if n < 2 or n != m:
        raise ValueError("Triangle must be square with at least two origin periods")
    if triangle.index.isna().any() or not triangle.index.is_unique:
        raise ValueError("Origin labels must be present and unique")
    if triangle.columns.isna().any() or not triangle.columns.is_unique:
        raise ValueError("Development labels must be present and unique")
    try:
        values = triangle.apply(pd.to_numeric, errors="raise").astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError("All observed claims must be numeric") from exc
    arr = values.to_numpy()
    for i in range(n):
        observed = arr[i, : n - i]
        future = arr[i, n - i :]
        if not np.isfinite(observed).all():
            raise ValueError(f"Missing or non-finite observed claims in origin row {i + 1}")
        if not np.isnan(future).all():
            raise ValueError(f"Future cells must be empty in origin row {i + 1}")
        if (observed < 0).any() or (not allow_decrease and (np.diff(observed) < 0).any()):
            raise ValueError(f"Cumulative claims must be nonnegative and nondecreasing in origin row {i + 1}")
    for age in range(n - 1):
        if arr[: n - age - 1, age].sum() <= 0:
            raise ValueError(f"Zero observed volume at development age {age + 1}")
    return values


def load_triangle(data: bytes, filename: str) -> pd.DataFrame:
    """Read a wide triangle: first column origin label, remaining columns ages."""
    if not data:
        raise ValueError("Empty file")
    suffix = filename.lower().rsplit(".", 1)[-1]
    try:
        if suffix == "csv":
            frame = pd.read_csv(BytesIO(data), index_col=0)
        elif suffix == "xlsx":
            frame = pd.read_excel(BytesIO(data), index_col=0, engine="openpyxl")
        else:
            raise ValueError("Supported file formats: .csv and .xlsx")
    except (OSError, UnicodeError, pd.errors.ParserError, ImportError) as exc:
        raise ValueError("Could not read triangle file; check format and Excel support") from exc
    result = validate_triangle(frame)
    result.index.name = None
    return result


def triangle_csv(triangle: pd.DataFrame) -> bytes:
    """Export the triangle as UTF-8 CSV with origin labels."""
    return triangle.to_csv(index_label="origin").encode("utf-8")
