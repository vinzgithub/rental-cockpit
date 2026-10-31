# Copyright © 2026 Vincent Fournet
"""Tests import the package from ``src`` without installing it."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "rental_cockpit"))  # engine tests import ``engine`` directly
