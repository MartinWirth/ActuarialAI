"""Read a long-form multi-segment CSV of cumulative claims triangles."""
from io import BytesIO

import pandas as pd

from .data_io import validate_triangle


def load_portfolio_csv(data: bytes) -> dict[str, pd.DataFrame]:
    """Require columns segment, origin, development, cumulative_paid.

    Each segment is pivoted to a square triangle. Development labels are sorted
    lexically; use sortable labels such as D01, D02, ... D12.
    """
    if not data:
        raise ValueError("Empty portfolio file")
    try:
        frame = pd.read_csv(BytesIO(data), dtype={"segment": str, "origin": str,
                                                   "development": str})
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise ValueError("Could not read portfolio CSV") from exc
    required = {"segment", "origin", "development", "cumulative_paid"}
    if not required.issubset(frame.columns):
        raise ValueError("Required columns: segment, origin, development, cumulative_paid")
    if frame.empty or frame[list(required)].isna().any().any():
        raise ValueError("Portfolio records must be nonempty and complete")
    if frame.duplicated(["segment", "origin", "development"]).any():
        raise ValueError("Duplicate segment/origin/development combinations")
    if (frame["segment"].str.strip() == "").any():
        raise ValueError("Segment names cannot be empty")
    output = {}
    for segment, group in frame.groupby("segment", sort=True):
        triangle = group.pivot(index="origin", columns="development",
                               values="cumulative_paid")
        triangle = triangle.sort_index().sort_index(axis=1)
        try:
            output[segment] = validate_triangle(triangle)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid triangle for segment {segment}: {exc}") from exc
    return output
