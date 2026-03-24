"""
Quality control run engine: execute a list of functions on incoming data.
Each function has a type (missing, range, statsmed_test, ...) and config; returns pass/fail and message.

Runners return (passed, message) or (passed, message, figure_base64) when a figure is produced.
"""
import io
import base64
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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


def _fig_to_base64() -> str:
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close("all")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def run_acceptance_bar(rows: list[dict], config: dict) -> tuple[bool, str, str]:
    """Horizontal acceptance/rejection bar chart for a binary column. config: { column }."""
    from statsmed.qc_graphics import acceptance_rejection_horizontal_bar

    column = config.get("column")
    if not column:
        return False, "No column specified", ""
    if not rows:
        return False, "No data rows", ""

    values = []
    for row in rows:
        v = row.get(column)
        if v is not None:
            try:
                values.append(float(v))
            except (TypeError, ValueError):
                pass

    if not values:
        return False, f"No numeric values found in '{column}'", ""

    accepted = sum(1 for v in values if v == 1)
    rejected = sum(1 for v in values if v == 0)
    n = accepted + rejected
    if n == 0:
        return False, f"No 0/1 values in '{column}'", ""

    acc_pct = 100 * accepted / n
    rej_pct = 100 * rejected / n
    message = (
        f"Total: {n}\n"
        f"Accepted: {accepted} ({acc_pct:.1f}%)\n"
        f"Rejected: {rejected} ({rej_pct:.1f}%)"
    )

    fig, ax = plt.subplots(figsize=(8, 2.4))
    acceptance_rejection_horizontal_bar(ax, accepted, rejected)
    figure_b64 = _fig_to_base64()

    return True, message, figure_b64


FUNCTION_RUNNERS = {
    "missing": run_missing,
    "range": run_range,
    "custom": run_custom,
    "statsmed_test": run_statsmed_test,
    "acceptance_bar": run_acceptance_bar,
}


def run_quality_checks(
    data: list[dict[str, Any]],
    functions: list[tuple[str, str, dict]],
) -> list[dict]:
    """
    Run a list of quality control functions on the data.
    functions: list of (name, function_type, config_dict)
    Returns list of { "name", "function_type", "passed", "message", optional "figure" }.
    """
    results = []
    for name, func_type, config in functions:
        runner = FUNCTION_RUNNERS.get(func_type, run_custom)
        outcome = runner(data, config or {})
        passed, message = outcome[0], outcome[1]
        figure = outcome[2] if len(outcome) > 2 else None
        entry: dict[str, Any] = {
            "name": name,
            "function_type": func_type,
            "passed": passed,
            "message": message,
        }
        if figure:
            entry["figure"] = figure
        results.append(entry)
    return results
