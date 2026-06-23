"""Shared low-level value types and reusable dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, TypeAlias

Vec3: TypeAlias = tuple[float, float, float]
Quat: TypeAlias = tuple[float, float, float, float]
Inertia6: TypeAlias = tuple[float, float, float, float, float, float]
AnnotationMap: TypeAlias = dict[str, str]

ZERO_VEC3: Final[Vec3] = (0.0, 0.0, 0.0)
IDENTITY_QUAT: Final[Quat] = (1.0, 0.0, 0.0, 0.0)




@dataclass(slots=True, kw_only=True, frozen=True)
class Transform:
    """Rigid transform using SI translation and a quaternion rotation."""

    translation: Vec3 = ZERO_VEC3
    rotation: Quat = IDENTITY_QUAT

    @classmethod
    def identity(cls) -> "Transform":
        """Return an identity transform."""

        return cls()
