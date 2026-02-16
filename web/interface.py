"""Registry mapping statsmed functions to web UI inputs.
Add one entry per test. The Flask app reads this and builds the UI automatically."""

import sys
import io
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from statsmed.statsmed import (
    stdnorm_test, get_desc, corr_two_gr, corr_scatter_figure,
    comp_two_gr_continuous,
    bland_altman_plot, bland_altman_bias_and_limits,
    acc_sens,
    compare_proportions_dep, compare_proportions_ind_sens_precision,
    ROC_fig,
    multivariate_linear_lasso, multivariate_logistic_lasso,
    mc_nemar_test,
    non_inferiority_ttest, non_superiority_ttest,
    non_inferiority_wilcoxon, non_superiority_wilcoxon, non_superiority_wilcoxon_abs,
    poisson_negbin_rate_change,
)


def _capture(func, *args, **kwargs):
    """Capture stdout from a statsmed function."""
    old = sys.stdout
    sys.stdout = buf = io.StringIO()
    try:
        func(*args, **kwargs)
    finally:
        sys.stdout = old
    return buf.getvalue()


def _fig_to_base64():
    """Convert current matplotlib figure to base64 string."""
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    plt.close('all')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def _docstring(func):
    """Return the first line of a function's docstring, or empty string."""
    doc = (func.__doc__ or '').strip()
    return doc.split('\n')[0].strip() if doc else ''


# ---------------------------------------------------------------------------
# Run functions: each takes (df, params) and returns (text, figure_or_None)
# ---------------------------------------------------------------------------

def run_normality(df, params):
    x = df[params["x"]].dropna().values.astype(float)
    text = _capture(stdnorm_test, x)
    return text, None


def run_descriptive(df, params):
    x = df[params["x"]].dropna().values.astype(float)
    text = _capture(get_desc, x, mode='all')
    return text, None


def run_correlation(df, params):
    sub = df[[params["x"], params["y"]]].dropna()
    x = sub[params["x"]].values.astype(float)
    y = sub[params["y"]].values.astype(float)
    text = _capture(corr_two_gr, x, y, mode='all')
    fig, ax = plt.subplots(figsize=(8, 6))
    corr_scatter_figure(x, y, ax, x_label=params["x"], y_label=params["y"], quiet=True)
    return text, _fig_to_base64()


def run_comparison(df, params):
    sub = df[[params["x"], params["y"]]].dropna()
    x = sub[params["x"]].values.astype(float)
    y = sub[params["y"]].values.astype(float)
    independent = params.get("independent", True)
    text = _capture(comp_two_gr_continuous, x, y, independent)
    return text, None


def run_bland_altman(df, params):
    sub = df[[params["x"], params["y"]]].dropna()
    x = sub[params["x"]].values.astype(float)
    y = sub[params["y"]].values.astype(float)
    text = _capture(bland_altman_bias_and_limits, x, y)
    fig, ax = plt.subplots(figsize=(8, 6))
    bland_altman_plot(x, y, ax, x_label=params["x"], y_label=params["y"])
    return text, _fig_to_base64()


def run_acc_sens(df, params):
    sub = df[[params["gt"], params["x"]]].dropna()
    gt = sub[params["gt"]].values.astype(float)
    x = sub[params["x"]].values.astype(float)
    text = _capture(acc_sens, gt, x)
    return text, None


def run_roc(df, params):
    sub = df[[params["true_base"], params["pred_value"]]].dropna()
    true_base = sub[params["true_base"]].values.astype(float)
    pred_value = sub[params["pred_value"]].values.astype(float)
    positive_label = params["positive_label"]
    nsamples = int(params.get("nsamples", 1000))
    fig, ax = plt.subplots(figsize=(8, 6))
    text = _capture(ROC_fig, true_base, pred_value, positive_label,
                    nsamples=nsamples, x=ax)
    return text, _fig_to_base64()


def run_compare_prop_dep(df, params):
    sub = df[[params["gt"], params["x"], params["y"]]].dropna()
    gt = sub[params["gt"]].values.astype(float)
    x = sub[params["x"]].values.astype(float)
    y = sub[params["y"]].values.astype(float)
    text = _capture(compare_proportions_dep, gt, x, y)
    return text, None


def run_compare_prop_ind(df, params):
    cols = [params["gt_x"], params["x"], params["gt_y"], params["y"]]
    sub = df[cols].dropna()
    gt_x = sub[params["gt_x"]].values.astype(float)
    x = sub[params["x"]].values.astype(float)
    gt_y = sub[params["gt_y"]].values.astype(float)
    y = sub[params["y"]].values.astype(float)
    text = _capture(compare_proportions_ind_sens_precision, gt_x, x, gt_y, y)
    return text, None


def run_mcnemar(df, params):
    sub = df[[params["test1"], params["test2"], params["gt"]]].dropna()
    test1 = sub[params["test1"]].values.astype(float)
    test2 = sub[params["test2"]].values.astype(float)
    gt = sub[params["gt"]].values.astype(float)
    text = _capture(mc_nemar_test, test1, test2, gt)
    return text, None


def _format_noninf(label, tstat, sig, pval, relad, alpha):
    """Format the output for non-inferiority / non-superiority tests."""
    lines = [
        label,
        f"Relative allowable difference: {relad}",
        f"Alpha: {alpha}",
        f"t-statistic: {tstat:.4f}",
        f"p-value: {pval:.6f}",
        f"Significant: {'Yes' if sig else 'No'}",
    ]
    if 'inferiority' in label.lower():
        lines.append(f"Conclusion: {'Non-inferiority established' if sig else 'Non-inferiority NOT established'}")
    else:
        lines.append(f"Conclusion: {'Non-superiority established' if sig else 'Non-superiority NOT established'}")
    return '\n'.join(lines)


def run_non_inf(df, params):
    sub = df[[params["x"], params["y"]]].dropna()
    x = sub[params["x"]].values.astype(float)
    y = sub[params["y"]].values.astype(float)
    relad = params["relad"]
    alpha = params["alpha"]
    method = params.get("method", "ttest")
    if method == "wilcoxon":
        tstat, sig, pval = non_inferiority_wilcoxon(x, y, relad, alpha)
        label = "Non-inferiority Wilcoxon test"
    else:
        tstat, sig, pval = non_inferiority_ttest(x, y, relad, alpha)
        label = "Non-inferiority t-test"
    return _format_noninf(label, tstat, sig, pval, relad, alpha), None


def run_non_sup(df, params):
    sub = df[[params["x"], params["y"]]].dropna()
    x = sub[params["x"]].values.astype(float)
    y = sub[params["y"]].values.astype(float)
    relad = params["relad"]
    alpha = params["alpha"]
    method = params.get("method", "ttest")
    if method == "wilcoxon":
        tstat, sig, pval = non_superiority_wilcoxon(x, y, relad, alpha)
        label = "Non-superiority Wilcoxon test"
    elif method == "wilcoxon_abs":
        tstat, sig, pval = non_superiority_wilcoxon_abs(x, y, relad, alpha)
        label = "Non-superiority Wilcoxon test (absolute)"
    else:
        tstat, sig, pval = non_superiority_ttest(x, y, relad, alpha)
        label = "Non-superiority t-test"
    return _format_noninf(label, tstat, sig, pval, relad, alpha), None


def run_multivar_linear(df, params):
    target_col = params["target"]
    feature_cols = params["features"]
    sub = df[[target_col] + feature_cols].dropna()
    target = sub[target_col].values.astype(float)
    data = [sub[c].values.astype(float) for c in feature_cols]
    text = _capture(multivariate_linear_lasso, data, target, columns=feature_cols)
    return text, None


def run_multivar_logistic(df, params):
    target_col = params["target"]
    feature_cols = params["features"]
    sub = df[[target_col] + feature_cols].dropna()
    target = sub[target_col].values.astype(float)
    data = [sub[c].values.astype(float) for c in feature_cols]
    text = _capture(multivariate_logistic_lasso, data, target, columns=feature_cols)
    return text, None


def run_poisson_negbin(df, params):
    time_col = params["time_col"]
    count_col = params["count_col"]
    model_type = params.get("model_type", "poisson")
    time_as = params.get("time_as", "categorical")
    text = _capture(poisson_negbin_rate_change, df,
                    time_col=time_col, count_col=count_col,
                    model=model_type, time_as=time_as)
    return text, None


# ---------------------------------------------------------------------------
# Test registry
# ---------------------------------------------------------------------------

TESTS = {
    "normality": {
        "label": "Normality Test",
        "description": _docstring(stdnorm_test),
        "inputs": [
            {"name": "x", "label": "Data column", "type": "column"},
        ],
        "run": run_normality,
    },
    "descriptive": {
        "label": "Descriptive Statistics",
        "description": _docstring(get_desc),
        "inputs": [
            {"name": "x", "label": "Data column", "type": "column"},
        ],
        "run": run_descriptive,
    },
    "correlation": {
        "label": "Correlation",
        "description": _docstring(corr_two_gr),
        "inputs": [
            {"name": "x", "label": "X column", "type": "column"},
            {"name": "y", "label": "Y column", "type": "column"},
        ],
        "run": run_correlation,
    },
    "comparison": {
        "label": "Compare Two Groups",
        "description": _docstring(comp_two_gr_continuous),
        "inputs": [
            {"name": "x", "label": "Group 1 column", "type": "column"},
            {"name": "y", "label": "Group 2 column", "type": "column"},
            {"name": "independent", "label": "Independent groups", "type": "boolean", "default": True},
        ],
        "run": run_comparison,
    },
    "bland_altman": {
        "label": "Bland-Altman Analysis",
        "description": _docstring(bland_altman_plot),
        "inputs": [
            {"name": "x", "label": "Measurement 1", "type": "column"},
            {"name": "y", "label": "Measurement 2", "type": "column"},
        ],
        "run": run_bland_altman,
    },
    "acc_sens": {
        "label": "Accuracy & Sensitivity",
        "description": _docstring(acc_sens),
        "inputs": [
            {"name": "gt", "label": "Ground truth (0/1)", "type": "column"},
            {"name": "x", "label": "Predictions (0/1)", "type": "column"},
        ],
        "run": run_acc_sens,
    },
    "roc": {
        "label": "ROC Curve & AUC",
        "description": "ROC curve with bootstrapped AUC and optimal threshold.",
        "inputs": [
            {"name": "true_base", "label": "True labels", "type": "column"},
            {"name": "pred_value", "label": "Predicted scores", "type": "column"},
            {"name": "positive_label", "label": "Positive label value", "type": "number", "default": 1},
            {"name": "nsamples", "label": "Bootstrap samples", "type": "number", "default": 1000},
        ],
        "run": run_roc,
    },
    "compare_prop_dep": {
        "label": "Compare Proportions (Dependent)",
        "description": "McNemar's test and z-test for paired binary outcomes.",
        "inputs": [
            {"name": "gt", "label": "Ground truth (0/1)", "type": "column"},
            {"name": "x", "label": "Method 1 (0/1)", "type": "column"},
            {"name": "y", "label": "Method 2 (0/1)", "type": "column"},
        ],
        "run": run_compare_prop_dep,
    },
    "compare_prop_ind": {
        "label": "Compare Proportions (Independent)",
        "description": "Two-proportion z-test for independent sensitivity and precision.",
        "inputs": [
            {"name": "gt_x", "label": "Ground truth 1 (0/1)", "type": "column"},
            {"name": "x", "label": "Predictions 1 (0/1)", "type": "column"},
            {"name": "gt_y", "label": "Ground truth 2 (0/1)", "type": "column"},
            {"name": "y", "label": "Predictions 2 (0/1)", "type": "column"},
        ],
        "run": run_compare_prop_ind,
    },
    "mcnemar": {
        "label": "McNemar's Test",
        "description": "McNemar's test for paired binary classification results.",
        "inputs": [
            {"name": "test1", "label": "Test 1 (0/1)", "type": "column"},
            {"name": "test2", "label": "Test 2 (0/1)", "type": "column"},
            {"name": "gt", "label": "Ground truth (0/1)", "type": "column"},
        ],
        "run": run_mcnemar,
    },
    "non_inf": {
        "label": "Non-Inferiority Test",
        "description": _docstring(non_inferiority_ttest),
        "inputs": [
            {"name": "x", "label": "Reference column", "type": "column"},
            {"name": "y", "label": "Test column", "type": "column"},
            {"name": "method", "label": "Method", "type": "select", "options": [
                {"value": "ttest", "label": "T-test"},
                {"value": "wilcoxon", "label": "Wilcoxon"},
            ], "default": "ttest"},
            {"name": "relad", "label": "Relative allowable difference", "type": "number", "default": 0.1},
            {"name": "alpha", "label": "Alpha", "type": "number", "default": 0.025},
        ],
        "run": run_non_inf,
    },
    "non_sup": {
        "label": "Non-Superiority Test",
        "description": _docstring(non_superiority_ttest),
        "inputs": [
            {"name": "x", "label": "Reference column", "type": "column"},
            {"name": "y", "label": "Test column", "type": "column"},
            {"name": "method", "label": "Method", "type": "select", "options": [
                {"value": "ttest", "label": "T-test"},
                {"value": "wilcoxon", "label": "Wilcoxon"},
                {"value": "wilcoxon_abs", "label": "Wilcoxon (absolute)"},
            ], "default": "ttest"},
            {"name": "relad", "label": "Relative allowable difference", "type": "number", "default": 0.1},
            {"name": "alpha", "label": "Alpha", "type": "number", "default": 0.025},
        ],
        "run": run_non_sup,
    },
    "multivar_linear": {
        "label": "Multivariate Linear Regression (Lasso)",
        "description": "Linear regression with L1 regularization and cross-validated alpha.",
        "inputs": [
            {"name": "target", "label": "Target column", "type": "column"},
            {"name": "features", "label": "Feature columns", "type": "multi_column"},
        ],
        "run": run_multivar_linear,
    },
    "multivar_logistic": {
        "label": "Multivariate Logistic Regression (Lasso)",
        "description": "Logistic regression with L1 regularization and AUC scoring.",
        "inputs": [
            {"name": "target", "label": "Target column (binary)", "type": "column"},
            {"name": "features", "label": "Feature columns", "type": "multi_column"},
        ],
        "run": run_multivar_logistic,
    },
    "poisson_negbin": {
        "label": "Poisson / NegBin Rate Change",
        "description": _docstring(poisson_negbin_rate_change),
        "inputs": [
            {"name": "time_col", "label": "Time column", "type": "column"},
            {"name": "count_col", "label": "Count column", "type": "column"},
            {"name": "model_type", "label": "Model", "type": "select", "options": [
                {"value": "poisson", "label": "Poisson"},
                {"value": "negbin", "label": "Negative Binomial"},
            ], "default": "poisson"},
            {"name": "time_as", "label": "Time treatment", "type": "select", "options": [
                {"value": "categorical", "label": "Categorical"},
                {"value": "trend", "label": "Trend"},
            ], "default": "categorical"},
        ],
        "run": run_poisson_negbin,
    },
}
