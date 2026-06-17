"""Enumerations for simulation configuration."""

from __future__ import annotations

from enum import StrEnum


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
