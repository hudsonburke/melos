"""Backend-neutral simulation settings for project-level configuration."""

from __future__ import annotations

from dataclasses import dataclass, field

from enum import StrEnum

from melos.core.common.ids import Identifier
from melos.core.project.enums import AssetRole
from melos.core.common.types import AnnotationMap, Vec3
from melos.core.common.units import ACCELERATION_UNIT, DEFAULT_GRAVITY


class SolverType(StrEnum):
    """MuJoCo-compatible constraint solver algorithms."""

    PGS = "PGS"
    CG = "CG"
    NEWTON = "Newton"


class IntegratorType(StrEnum):
    """MuJoCo-compatible numerical integrators."""

    EULER = "euler"
    IMPLICIT = "implicit"
    IMPLICITFAST = "implicitfast"
    RK4 = "rk4"


@dataclass(slots=True, kw_only=True)
class SimulationConfig:
    """Thin runtime-facing simulation and compilation preferences."""

    compile_target: str = "mujoco"
    gravity: Vec3 = field(default=DEFAULT_GRAVITY, metadata={"unit": ACCELERATION_UNIT})
    time_step: float = 0.001
    duration: float | None = None
    visual_asset_roles: list[AssetRole] = field(
        default_factory=lambda: [AssetRole.VISUAL]
    )
    collision_asset_roles: list[AssetRole] = field(
        default_factory=lambda: [AssetRole.COLLISION, AssetRole.SIMULATION]
    )
    initial_coordinate_values: dict[Identifier, float] = field(default_factory=dict)
    solver_type: SolverType = SolverType.NEWTON
    solver_iterations: int = 100
    solver_tolerance: float = 1e-8
    noslip_iterations: int = 0
    integrator: IntegratorType = IntegratorType.IMPLICITFAST
    record_sensors: bool = True
    record_interval: int = 1
    initial_state_name: str | None = None
    keyframes: dict[str, dict[Identifier, float]] = field(default_factory=dict)
    annotations: AnnotationMap = field(default_factory=dict)
