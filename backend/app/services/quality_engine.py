"""
Quality control run engine: execute a list of functions on incoming data.
Each function has a type (missing, range, statsmed_test, ...) and config; returns pass/fail and message.
"""
from typing import Any

import pandas as pd

from .run_analysis import run_test_with_df


def run_missing(rows: list[dict], config: dict) -> tuple[bool, str]:
    """Check for missing/null values in specified columns."""
    columns = config.get("columns") or []
    if not columns:
        return False, "No columns specified"
    n = len(rows)
    missing_count = 0
    for row in rows:
        for col in columns:
            val = row.get(col)
            if val is None or (isinstance(val, float) and str(val) == "nan") or val == "":
                missing_count += 1
                break
    if missing_count == 0:
        return True, f"All {n} rows have no missing values in {columns}"
    return False, f"{missing_count} of {n} rows have missing values in {columns}"


def run_range(rows: list[dict], config: dict) -> tuple[bool, str]:
    """Check that values in column are within min/max (inclusive)."""
    column = config.get("column")
    min_val = config.get("min")
    max_val = config.get("max")
    if column is None:
        return False, "No column specified"
    if min_val is None and max_val is None:
        return False, "Specify at least min or max"
    out_of_range = []
    for i, row in enumerate(rows):
        val = row.get(column)
        if val is None:
            continue
        try:
            v = float(val)
        except (TypeError, ValueError):
            out_of_range.append((i, val))
            continue
        if min_val is not None and v < min_val:
            out_of_range.append((i, val))
        elif max_val is not None and v > max_val:
            out_of_range.append((i, val))
    if not out_of_range:
        return True, f"All values in '{column}' within range"
    return False, f"{len(out_of_range)} value(s) out of range: {out_of_range[:5]}{'...' if len(out_of_range) > 5 else ''}"


def run_custom(rows: list[dict], config: dict) -> tuple[bool, str]:
    """Placeholder for custom logic; can be extended later."""
    return True, "Custom check not implemented (placeholder)"


def run_statsmed_test(rows: list[dict], config: dict) -> tuple[bool, str]:
    """Run a statsmed test (from TESTS) with column mapping. config: { test_id, params }."""
    test_id = config.get("test_id")
    params = config.get("params") or {}
    if not test_id:
        return False, "No test_id in config"
    if not rows:
        return False, "No data rows"
    try:
        df = pd.DataFrame(rows)
        text, _ = run_test_with_df(df, test_id, params)
        passed = "Error:" not in text
        return passed, text
    except Exception as e:
        return False, str(e)


FUNCTION_RUNNERS = {
    "missing": run_missing,
    "range": run_range,
    "custom": run_custom,
    "statsmed_test": run_statsmed_test,
}


def run_quality_checks(
    data: list[dict[str, Any]],
    functions: list[tuple[str, str, dict]],
) -> list[dict]:
    """
    Run a list of quality control functions on the data.
    functions: list of (name, function_type, config_dict)
    Returns list of { "name", "function_type", "passed", "message" }.
    """
    results = []
    for name, func_type, config in functions:
        runner = FUNCTION_RUNNERS.get(func_type, run_custom)
        passed, message = runner(data, config or {})
        results.append({
            "name": name,
            "function_type": func_type,
            "passed": passed,
            "message": message,
        })
    return results
