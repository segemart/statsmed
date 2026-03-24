"""
Quality-control style figures: simple matplotlib visuals for binary outcomes.

Reusable building blocks for tests and reporting (e.g. acceptance vs rejection).
"""

from __future__ import annotations

from matplotlib.axes import Axes


def acceptance_rejection_horizontal_bar(
    ax: Axes,
    accepted: int,
    rejected: int,
    *,
    color_accepted: str = "#2e7d32",
    color_rejected: str = "#c62828",
    bar_height: float = 0.45,
    y_center: float = 0.0,
) -> None:
    """
    Draw a single horizontal stacked bar from 0 to 1: accepted (green) then rejected (red).

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Target axes.
    accepted, rejected : int
        Counts of 1s and 0s; proportions are accepted / (accepted + rejected), etc.
    color_accepted, color_rejected : str
        Fill colors for the two segments.
    bar_height : float
        Vertical thickness of the bar in data coordinates.
    y_center : float
        Vertical center of the bar on the y-axis.
    """
    n = int(accepted) + int(rejected)
    ax.set_facecolor("white")
    if n <= 0:
        ax.set_xlim(0, 1)
        ax.set_ylim(-0.5, 0.5)
        ax.text(0.5, 0.0, "No data", ha="center", va="center", fontsize=11, color="0.35")
        ax.set_yticks([])
        ax.set_xticks([0, 0.5, 1])
        ax.set_xticklabels(["0%", "50%", "100%"])
        ax.set_xlabel("Share")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        return

    acc_frac = accepted / n
    rej_frac = rejected / n

    ax.barh(
        y_center,
        acc_frac,
        left=0.0,
        height=bar_height,
        color=color_accepted,
        label="Accepted",
        edgecolor="white",
        linewidth=0.8,
    )
    ax.barh(
        y_center,
        rej_frac,
        left=acc_frac,
        height=bar_height,
        color=color_rejected,
        label="Rejected",
        edgecolor="white",
        linewidth=0.8,
    )

    ax.set_xlim(0, 1)
    ax.set_ylim(y_center - 0.5, y_center + 0.5)
    ax.set_yticks([])
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("Share")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    # Optional percentage labels inside segments when wide enough
    if acc_frac >= 0.12:
        ax.text(
            acc_frac / 2,
            y_center,
            f"{100 * acc_frac:.1f}%",
            ha="center",
            va="center",
            color="white",
            fontsize=10,
            fontweight="bold",
        )
    if rej_frac >= 0.12:
        ax.text(
            acc_frac + rej_frac / 2,
            y_center,
            f"{100 * rej_frac:.1f}%",
            ha="center",
            va="center",
            color="white",
            fontsize=10,
            fontweight="bold",
        )

    ax.set_title(f"n = {n}  (accepted: {accepted}, rejected: {rejected})", fontsize=12, pad=8)
