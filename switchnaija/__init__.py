"""SwitchNaija: open-data climate and energy tools for Nigerian communities.

Modules
-------
energy   : generator-to-solar planner (load, grid outages, dispatch, optimiser, economics)
battery  : battery ageing, lifetime cost and end-of-life guidance ("Battery Afterlife")
flood    : rainfall extremes and flood exposure of schools and markets ("FloodSafe", in progress)
sources  : connectors to public data (PVGIS, NASA POWER)
"""

from .config import load_defaults, towns

__all__ = ["load_defaults", "towns"]
__version__ = "0.1.0"
