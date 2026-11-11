"""Shareable 'impact card' image (PNG) for WhatsApp and social media."""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _naira(x: float) -> str:
    if abs(x) >= 1e6:
        return f"N{x / 1e6:.1f}m"
    if abs(x) >= 1e3:
        return f"N{x / 1e3:.0f}k"
    return f"N{x:.0f}"


def impact_card(place: str, system: str, savings_per_year_ngn: float, payback_years: float | None,
                fuel_saved_litres: float, co2_saved_t: float, battery_note: str) -> bytes:
    """Return a 1080x1080 PNG summarising the switch."""
    fig = plt.figure(figsize=(6, 6), dpi=180)
    fig.patch.set_facecolor("#0f3d2e")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    white, sun = "#ffffff", "#f6c445"
    ax.text(0.06, 0.92, "SwitchNaija", color=sun, fontsize=22, weight="bold")
    ax.text(0.06, 0.87, f"Switching from generator to solar in {place}", color=white, fontsize=11)
    ax.text(0.06, 0.82, system, color=white, fontsize=10, alpha=0.85)

    tiles = [
        ("Saved per year", _naira(savings_per_year_ngn)),
        ("Pays back in", "n/a" if payback_years is None else f"{payback_years * 12:.0f} months"),
        ("Fuel avoided", f"{fuel_saved_litres:,.0f} L/yr"),
        ("CO2 avoided", f"{co2_saved_t:.1f} t/yr"),
    ]
    for i, (label, value) in enumerate(tiles):
        x = 0.06 + (i % 2) * 0.46
        y = 0.52 - (i // 2) * 0.22
        ax.add_patch(plt.Rectangle((x, y), 0.42, 0.19, color="#145a43", transform=ax.transAxes))
        ax.text(x + 0.03, y + 0.12, value, color=sun, fontsize=19, weight="bold")
        ax.text(x + 0.03, y + 0.04, label, color=white, fontsize=10)
    ax.text(0.06, 0.20, battery_note, color=white, fontsize=8.5, wrap=True)
    ax.text(0.06, 0.08, "Free tool, open data: PVGIS (EU JRC), NBS, NERC. Estimates, not a quote.",
            color=white, fontsize=7.5, alpha=0.8)
    ax.text(0.06, 0.04, "BioBuild Africa", color=sun, fontsize=9, weight="bold")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()
