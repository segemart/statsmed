"""
Quality control run engine: execute a list of functions on incoming data.
Each function has a type (missing, range, statsmed_test, ...) and config; returns pass/fail and message.

Runners return (passed, message) or (passed, message, figure_base64) when a figure is produced.
"""
import io
import base64
from typing import Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .run_analysis import run_test_with_df
from statsmed.statsmed import laney_p_chart as _statsmed_laney_p_chart


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


def run_acceptance_bar(rows: list[dict], config: dict) -> tuple[bool, str, dict]:
    """Acceptance/rejection bar for a binary column. Returns structured chart_data for frontend CSS rendering."""
    column = config.get("column")
    if not column:
        return False, "No column specified", {}
    if not rows:
        return False, "No data rows", {}

    values = []
    for row in rows:
        v = row.get(column)
        if v is not None:
            try:
                values.append(float(v))
            except (TypeError, ValueError):
                pass

    if not values:
        return False, f"No numeric values found in '{column}'", {}

    accepted = sum(1 for v in values if v == 1)
    rejected = sum(1 for v in values if v == 0)
    n = accepted + rejected
    if n == 0:
        return False, f"No 0/1 values in '{column}'", {}

    acc_pct = 100 * accepted / n
    rej_pct = 100 * rejected / n
    message = (
        f"Total: {n}\n"
        f"Accepted: {accepted} ({acc_pct:.1f}%)\n"
        f"Rejected: {rejected} ({rej_pct:.1f}%)"
    )

    chart_data = {
        "type": "acceptance_bar",
        "accepted": accepted,
        "rejected": rejected,
        "total": n,
        "accepted_pct": round(acc_pct, 1),
        "rejected_pct": round(rej_pct, 1),
    }

    return True, message, chart_data


def run_acceptance_history(rows: list[dict], config: dict) -> tuple[bool, str, dict]:
    """Placeholder runner; actual history data is injected by the router after the run is saved."""
    return True, "Acceptance history chart", {"type": "acceptance_history", "points": []}


def run_laney_p_chart(rows: list[dict], config: dict) -> tuple[bool, str, dict]:
    """Placeholder runner; actual Laney p' chart data is injected by the router from historical runs."""
    k = config.get("k", 3.0)
    return True, "Laney p\u2032 chart", {"type": "laney_p_chart", "pbar": 0, "sigma_z": 0, "k": k, "points": []}


def compute_laney_p_chart(
    history_points: list[dict],
    k: float = 3.0,
    clip_limits: bool = True,
) -> dict:
    """
    Compute Laney p' chart from historical acceptance data.

    Delegates the statistical computation to statsmed.statsmed.laney_p_chart
    and formats the result as structured chart_data for the frontend.

    history_points: list of dicts with keys: date, accepted, total, run_id.
    """
    empty = {"type": "laney_p_chart", "pbar": 0, "sigma_z": 0, "k": k, "points": []}

    if len(history_points) < 2:
        return empty

    x_arr = np.array([pt["accepted"] for pt in history_points], dtype=float)
    n_arr = np.array([pt["total"] for pt in history_points], dtype=float)

    if np.any(n_arr <= 0):
        return empty

    try:
        result = _statsmed_laney_p_chart(x_arr, n_arr, k=k, clip_limits=clip_limits, quiet=True)
    except ValueError:
        p = x_arr / n_arr
        pbar = float(x_arr.sum() / n_arr.sum())
        pts = [
            {
                "date": pt["date"],
                "p": round(float(p[i]), 4),
                "lcl": 0.0,
                "ucl": 1.0,
                "n": int(n_arr[i]),
                "out_of_control": False,
                "run_id": pt["run_id"],
            }
            for i, pt in enumerate(history_points)
        ]
        return {"type": "laney_p_chart", "pbar": round(pbar, 4), "sigma_z": 0, "k": k, "points": pts}

    pts = [
        {
            "date": pt["date"],
            "p": round(float(result["p"][i]), 4),
            "lcl": round(float(result["lcl"][i]), 4),
            "ucl": round(float(result["ucl"][i]), 4),
            "n": int(n_arr[i]),
            "out_of_control": bool(result["out_of_control"][i]),
            "run_id": pt["run_id"],
        }
        for i, pt in enumerate(history_points)
    ]

    return {
        "type": "laney_p_chart",
        "pbar": round(result["pbar"], 4),
        "sigma_z": round(result["sigma_z"], 4),
        "k": result["k"],
        "points": pts,
    }


FUNCTION_RUNNERS = {
    "missing": run_missing,
    "range": run_range,
    "custom": run_custom,
    "statsmed_test": run_statsmed_test,
    "acceptance_bar": run_acceptance_bar,
    "acceptance_history": run_acceptance_history,
    "laney_p_chart": run_laney_p_chart,
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
        extra = outcome[2] if len(outcome) > 2 else None
        entry: dict[str, Any] = {
            "name": name,
            "function_type": func_type,
            "passed": passed,
            "message": message,
        }
        if isinstance(extra, str) and extra:
            entry["figure"] = extra
        elif isinstance(extra, dict) and extra:
            entry["chart_data"] = extra
        results.append(entry)
    return results
