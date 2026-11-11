"""SwitchNaija energy planner: generator to solar plus battery."""

from .load import Appliance, LoadProfile, PRESETS
from .grid import outage_schedule
from .generator import Generator
from .dispatch import DispatchResult, simulate
from .planner import Site, PlanResult, Option, plan, sensitivity, calibrate_generator

__all__ = [
    "Appliance", "LoadProfile", "PRESETS", "outage_schedule", "Generator",
    "DispatchResult", "simulate", "Site", "PlanResult", "Option", "plan",
    "sensitivity", "calibrate_generator",
]
