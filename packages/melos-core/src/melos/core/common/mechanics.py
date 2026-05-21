"""Shared mechanics-oriented dataclasses.

These types are reusable across domains, but they are more specific than the
mathematical primitives in ``melos.core.common.types``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .types import Inertia6, Vec3
from .units import INERTIA_UNIT, LENGTH_UNIT, MASS_UNIT


@dataclass(slots=True, kw_only=True)
class InertialProperties:
    """Inertial properties for a rigid body or rigid link."""

    mass: float | None = field(default=None, metadata={"unit": MASS_UNIT})
    center_of_mass: Vec3 | None = field(default=None, metadata={"unit": LENGTH_UNIT})
    inertia_about_com: Inertia6 | None = field(
        default=None, metadata={"unit": INERTIA_UNIT}
    )
