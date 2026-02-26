"""
Run statsmed analysis: read dataframe, apply params and optional categorical conversion, call test.
Uses web.interface.TESTS; repo root must be on PYTHONPATH when running the backend.
"""
import json
import sys
from pathlib import Path
import pandas as pd

# Ensure repo root is on path (statsmed repo, so backend/app/services -> repo = parents[3])
_repo_root = Path(__file__).resolve().parents[3]
if _repo_root not in sys.path:
    sys.path.insert(0, str(_repo_root))

from web.interface import TESTS


def read_df(filepath: str, csv_delimiter: str = ",") -> pd.DataFrame:
    if filepath.endswith(".csv"):
        return pd.read_csv(filepath, sep=csv_delimiter)
    return pd.read_excel(filepath)


def run_test(filepath: str, csv_delimiter: str, test_id: str, params: dict) -> tuple[str, str | None]:
    """
    Run one test. Returns (text, figure_base64_or_none).
    params: dict with keys matching test inputs (column names, booleans, numbers, etc.)
    """
    if test_id not in TESTS:
        raise ValueError(f"Unknown test: {test_id}")
    test = TESTS[test_id]
    df = read_df(filepath, csv_delimiter)

    # Normalize params from JSON: booleans may come as true/false, multi_column as list
    col_names = []
    cols_to_convert = []
    for inp in test["inputs"]:
        name = inp["name"]
        if name not in params:
            if inp["type"] == "boolean" and inp.get("default"):
                params[name] = True
            elif inp["type"] in ("number", "select") and "default" in inp:
                params[name] = inp["default"]
            else:
                raise ValueError(f"Missing parameter: {name}")
        if inp["type"] == "column":
            col_names.append(params[name])
            if params.get(f"convert_{name}"):
                cols_to_convert.append(params[name])
        elif inp["type"] == "multi_column":
            col_names.extend(params.get(name, []))
            for c in params.get("convert_multi_col", []):
                if c not in cols_to_convert:
                    cols_to_convert.append(c)

    convert_mode = params.get("convert_mode", "shared")
    conversions = []
    if cols_to_convert:
        if convert_mode == "shared":
            all_values = sorted(
                set(str(v) for col in cols_to_convert for v in df[col].dropna().unique())
            )
            shared_mapping = {v: i for i, v in enumerate(all_values)}
            for col in cols_to_convert:
                df[col] = df[col].astype(str).map(shared_mapping).astype(int)
            conversions.append("Shared categorical mapping applied.")
        else:
            for col in cols_to_convert:
                uniques = sorted(df[col].dropna().unique(), key=str)
                mapping = {str(v): i for i, v in enumerate(uniques)}
                df[col] = df[col].astype(str).map(mapping).astype(int)
            conversions.append("Independent categorical mapping per column.")

    dup_warning = ""
    if len(col_names) != len(set(col_names)):
        dup_warning = "WARNING: The same column was selected for multiple inputs. Results may be erroneous.\n\n"

    # Build clean params for test: only input names, with correct types
    run_params = {}
    for inp in test["inputs"]:
        name = inp["name"]
        val = params.get(name)
        if inp["type"] == "boolean":
            run_params[name] = val in (True, "true", "on", 1)
        elif inp["type"] == "number":
            run_params[name] = float(val) if val is not None else inp.get("default", 0)
        elif inp["type"] == "multi_column":
            run_params[name] = val if isinstance(val, list) else ([val] if val else [])
        else:
            run_params[name] = val

    try:
        text, figure = test["run"](df, run_params)
    except Exception as e:
        text, figure = f"Error: {e}", None

    if dup_warning:
        text = dup_warning.strip() + "\n\n" + text
    if conversions:
        text = "\n".join(conversions) + "\n\n" + text

    return text, figure


def run_test_with_df(df: pd.DataFrame, test_id: str, params: dict) -> tuple[str, str | None]:
    """
    Run one statsmed test on an existing DataFrame. Same as run_test but no file read.
    Used by quality control. Returns (text, figure_base64_or_none).
    """
    if test_id not in TESTS:
        raise ValueError(f"Unknown test: {test_id}")
    test = TESTS[test_id]
    params = dict(params)

    col_names = []
    cols_to_convert = []
    for inp in test["inputs"]:
        name = inp["name"]
        if name not in params:
            if inp["type"] == "boolean" and inp.get("default"):
                params[name] = True
            elif inp["type"] in ("number", "select") and "default" in inp:
                params[name] = inp["default"]
            else:
                raise ValueError(f"Missing parameter: {name}")
        if inp["type"] == "column":
            col_names.append(params[name])
            if params.get(f"convert_{name}"):
                cols_to_convert.append(params[name])
        elif inp["type"] == "multi_column":
            col_names.extend(params.get(name, []))
            for c in params.get("convert_multi_col", []):
                if c not in cols_to_convert:
                    cols_to_convert.append(c)

    convert_mode = params.get("convert_mode", "shared")
    if cols_to_convert:
        if convert_mode == "shared":
            all_values = sorted(
                set(str(v) for col in cols_to_convert for v in df[col].dropna().unique())
            )
            shared_mapping = {v: i for i, v in enumerate(all_values)}
            for col in cols_to_convert:
                df[col] = df[col].astype(str).map(shared_mapping).astype(int)
        else:
            for col in cols_to_convert:
                uniques = sorted(df[col].dropna().unique(), key=str)
                mapping = {str(v): i for i, v in enumerate(uniques)}
                df[col] = df[col].astype(str).map(mapping).astype(int)

    dup_warning = ""
    if len(col_names) != len(set(col_names)):
        dup_warning = "WARNING: The same column was selected for multiple inputs.\n\n"

    run_params = {}
    for inp in test["inputs"]:
        name = inp["name"]
        val = params.get(name)
        if inp["type"] == "boolean":
            run_params[name] = val in (True, "true", "on", 1)
        elif inp["type"] == "number":
            run_params[name] = float(val) if val is not None else inp.get("default", 0)
        elif inp["type"] == "multi_column":
            run_params[name] = val if isinstance(val, list) else ([val] if val else [])
        else:
            run_params[name] = val

    try:
        text, figure = test["run"](df, run_params)
    except Exception as e:
        text, figure = f"Error: {e}", None

    if dup_warning:
        text = dup_warning.strip() + "\n\n" + text
    return text, figure


def get_tests_schema():
    """Return tests config for frontend: id, label, description, inputs (no run function)."""
    return {
        tid: {
            "id": tid,
            "label": t["label"],
            "description": t["description"],
            "inputs": t["inputs"],
        }
        for tid, t in TESTS.items()
    }
