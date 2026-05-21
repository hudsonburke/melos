"""Shared enums for backend-neutral melos concepts."""

from __future__ import annotations

from enum import StrEnum


class AssetRole(StrEnum):
    """Intended purpose of an asset in the authoring or simulation pipeline."""

    IMAGING = "imaging"
    SEGMENTATION = "segmentation"
    VISUAL = "visual"
    COLLISION = "collision"
    SIMULATION = "simulation"
    FITTING = "fitting"
    ANALYSIS = "analysis"


class CompileTarget(StrEnum):
    """Simulation backend targets supported by the core model."""

    MUJOCO = "mujoco"
