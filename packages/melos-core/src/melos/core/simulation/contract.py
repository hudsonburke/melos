"""Compiler-facing contract notes for simulation backends.

This module does not implement backend export. Instead, it captures the minimum
assumptions that a backend compiler such as ``melos.sim.mujoco`` may rely on when it
consumes a validated ``Project``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, kw_only=True)
class CompilerExpectation:
    """Single compiler-facing expectation derived from the core schema."""

    key: str
    description: str


@dataclass(slots=True, kw_only=True)
class BackendContract:
    """Structured description of what a backend compiler may assume."""

    backend: str
    assumptions: list[CompilerExpectation] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


MUJOCO_BACKEND_CONTRACT = BackendContract(
    backend="mujoco",
    assumptions=[
        CompilerExpectation(
            key="validated_project",
            description=(
                "Input projects should already pass melos.core validation before "
                "backend compilation begins."
            ),
        ),
        CompilerExpectation(
            key="rigid_body_focus",
            description=(
                "Anatomical links, device links, joints, and attachments define the "
                "rigid-body structure that a MuJoCo compiler should lower into MJCF."
            ),
        ),
        CompilerExpectation(
            key="frame_relative_authoring",
            description=(
                "Frames and frame-relative points are canonical authoring anchors; "
                "a compiler is responsible for converting them into backend-friendly "
                "poses, sites, and geoms."
            ),
        ),
        CompilerExpectation(
            key="path_muscle_canonical",
            description=(
                "Muscles are canonically represented as physiology plus ordered path "
                "points, with optional wrap geometry and optional associated meshes."
            ),
        ),
        CompilerExpectation(
            key="asset_role_selection",
            description=(
                "SimulationConfig.visual_asset_roles and collision_asset_roles define "
                "which asset roles should be considered for rendering and collision "
                "during backend compilation."
            ),
        ),
        CompilerExpectation(
            key="control_interface_stability",
            description=(
                "Observation and command channels define stable external names even if "
                "the backend uses different internal object names."
            ),
        ),
    ],
    outputs=[
        "MJCF model text or equivalent structured MJCF builder output",
        "backend-specific asset manifest",
        "signal/control map for observations and commands",
        "optional compile report and warnings",
    ],
    notes=[
        "The compiler should treat melos.core as the semantic source of truth, not as a literal MJCF mirror.",
        "Associated muscle geometry may inform export or visualization, but path-based muscle definition remains canonical in v0.1.",
        "Wrap geometry is typed in the core model; a MuJoCo compiler may approximate unsupported wrap behaviors while preserving provenance in sidecar outputs.",
    ],
)
