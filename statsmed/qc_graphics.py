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
    bar_height: float = 0.6,
    y_center: float = 0.0,
) -> None:
    """
    Draw a single horizontal stacked bar: accepted (green) then rejected (red).

    Labels with count and percentage are rendered inside each segment.
    No axes, ticks, spines or legend — clean appearance matching statsmed style.
    """
    n = int(accepted) + int(rejected)
    ax.set_facecolor("white")

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    if n <= 0:
        ax.set_xlim(0, 1)
        ax.set_ylim(-0.5, 0.5)
        ax.text(0.5, 0.0, "No data", ha="center", va="center", fontsize=14, color="0.4")
        return

    acc_frac = accepted / n
    rej_frac = rejected / n

    ax.barh(
        y_center,
        acc_frac,
        left=0.0,
        height=bar_height,
        color=color_accepted,
        edgecolor="white",
        linewidth=0.8,
    )
    ax.barh(
        y_center,
        rej_frac,
        left=acc_frac,
        height=bar_height,
        color=color_rejected,
        edgecolor="white",
        linewidth=0.8,
    )

    ax.set_xlim(0, 1)
    ax.set_ylim(y_center - 0.5, y_center + 0.5)

    if acc_frac >= 0.10:
        ax.text(
            acc_frac / 2,
            y_center,
            f"Accepted: {accepted} ({100 * acc_frac:.1f}%)",
            ha="center",
            va="center",
            color="white",
            fontsize=12,
            fontweight="bold",
        )
    if rej_frac >= 0.10:
        ax.text(
            acc_frac + rej_frac / 2,
            y_center,
            f"Rejected: {rejected} ({100 * rej_frac:.1f}%)",
            ha="center",
            va="center",
            color="white",
            fontsize=12,
            fontweight="bold",
        )

    ax.set_title(f"n = {n}", fontsize=14, pad=8)
