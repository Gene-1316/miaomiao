"""Bundled resources are read-only; packaged saves live outside extraction."""
from pathlib import Path
import os
import sys

RESOURCE_ROOT = Path(__file__).resolve().parents[1]


def data_root() -> Path:
    if getattr(sys, "frozen", False):
        local = os.environ.get("LOCALAPPDATA")
        return (Path(local) if local else Path.home() / "AppData" / "Local") / "miaomiao"
    return RESOURCE_ROOT


def default_save() -> Path:
    return data_root() / "save_data" / "pet.json"


def log_root() -> Path:
    return data_root() / ("logs" if getattr(sys, "frozen", False) else "artifacts")
