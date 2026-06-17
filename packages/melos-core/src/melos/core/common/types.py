"""Shared low-level value types and reusable dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final, TypeAlias

Vec3: TypeAlias = tuple[float, float, float]
Quat: TypeAlias = tuple[float, float, float, float]
Inertia6: TypeAlias = tuple[float, float, float, float, float, float]
AnnotationMap: TypeAlias = dict[str, str]


class AssetRole(StrEnum):
    """Intended purpose of an asset in the authoring or simulation pipeline."""

    IMAGING = "imaging"
    SEGMENTATION = "segmentation"
    VISUAL = "visual"
    COLLISION = "collision"
    SIMULATION = "simulation"
    FITTING = "fitting"
    ANALYSIS = "analysis"


ZERO_VEC3: Final[Vec3] = (0.0, 0.0, 0.0)
IDENTITY_QUAT: Final[Quat] = (1.0, 0.0, 0.0, 0.0)
ZERO_INERTIA6: Final[Inertia6] = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


@dataclass(slots=True, kw_only=True, frozen=True)
class Bounds:
    """Optional lower and upper bounds for scalar values."""

    lower: float | None = None
    upper: float | None = None


@dataclass(slots=True, kw_only=True)
class InertialProperties:
    """Inertial properties for a rigid body or rigid link."""

    mass: float | None = field(default=None, metadata={"unit": "kg"})
    center_of_mass: Vec3 | None = field(default=None, metadata={"unit": "m"})
    inertia_about_com: Inertia6 | None = field(
        default=None, metadata={"unit": "kg*m^2"}
    )


@dataclass(slots=True, kw_only=True, frozen=True)
class Transform:
    """Rigid transform using SI translation and a quaternion rotation."""

    translation: Vec3 = ZERO_VEC3
    rotation: Quat = IDENTITY_QUAT

    @classmethod
    def identity(cls) -> "Transform":
        """Return an identity transform."""

        return cls()
