"""Shared helpers for the technical_analysis module."""

import pandas as pd


def safe_last(data: pd.Series | pd.DataFrame | None, col: int = 0) -> float | None:
    """Extract the last value from a Series or the given column of a DataFrame."""
    if data is None:
        return None
    series = data.iloc[:, col] if isinstance(data, pd.DataFrame) else data
    if series.empty:
        return None
    val = series.iloc[-1]
    return None if pd.isna(val) else float(val)
