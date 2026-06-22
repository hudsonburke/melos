"""Unit conventions and unit-conversion helpers.

The core model uses SI units internally. Importers and exporters should convert
to and from their native conventions at the system boundary.
"""

from __future__ import annotations

from typing import Final
from .types import Vec3

LENGTH_UNIT: Final[str] = "m"
MASS_UNIT: Final[str] = "kg"
TIME_UNIT: Final[str] = "s"
ANGLE_UNIT: Final[str] = "rad"
FORCE_UNIT: Final[str] = "N"
TORQUE_UNIT: Final[str] = f"{FORCE_UNIT}*{LENGTH_UNIT}"
INERTIA_UNIT: Final[str] = f"{MASS_UNIT}*{LENGTH_UNIT}^2"
ACCELERATION_UNIT: Final[str] = f"{LENGTH_UNIT}/{TIME_UNIT}^2"

DEFAULT_GRAVITY: Final[Vec3] = (0.0, 0.0, -9.81)

