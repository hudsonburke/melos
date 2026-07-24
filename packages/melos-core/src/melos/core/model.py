"""Canonical Melos data model.

Single source of truth for all skeleton, joint, cable, landmark, and
exoskeleton types.  Every other module in the codebase imports from here.

This module has **no dependencies** beyond the Python stdlib and pydantic.
It defines the shapes that JSON, MJCF, and Proteus all agree on.
"""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, Field


# ── Core primitives ───────────────────────────────────────────────────────


class Vec3(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class Quat(BaseModel):
    """Quaternion in (w, x, y, z) order."""
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


# ── Skeleton components ───────────────────────────────────────────────────


class JointLimits(BaseModel):
    lower: float = -math.inf
    upper: float = math.inf


class JointDef(BaseModel):
    joint_type: str = "CustomJoint"
    axis: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    limits: JointLimits = Field(default_factory=JointLimits)
    parent_link: str = ""
    child_link: str = ""
    default_qpos: float = 0.0


class LinkDef(BaseModel):
    name: str = ""
    mass: float = 0.0
    center_of_mass: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    inertia: list[float] = Field(default_factory=lambda: [0.0] * 6)
    graphics_file: str = ""
    visible: bool = True


class LinkTransform(BaseModel):
    translation: tuple[float, float, float] = (0, 0, 0)
    rotation: tuple[float, float, float, float] = (1, 0, 0, 0)  # (w, x, y, z)


class SkeletonState(BaseModel):
    joints: dict[str, JointDef] = Field(default_factory=dict)
    links: dict[str, LinkDef] = Field(default_factory=dict)
    transforms: dict[str, LinkTransform] = Field(default_factory=dict)
    parent_map: dict[str, str] = Field(default_factory=dict)
    order: list[str] = Field(default_factory=list)
    descendants: dict[str, list[str]] = Field(default_factory=dict)


class ModelState(BaseModel):
    name: str = ""
    skeleton: SkeletonState = Field(default_factory=SkeletonState)


# ── Patch types (API edits) ──────────────────────────────────────────────


class JointPatch(BaseModel):
    joint_type: str | None = None
    axis: list[float] | None = None
    limits: JointLimits | None = None
    default_qpos: float | None = None


class TransformPatch(BaseModel):
    translation: tuple[float, float, float] | None = None
    rotation: tuple[float, float, float, float] | None = None


# ── Cable / tendon components ─────────────────────────────────────────────


class CableViaPoint(BaseModel):
    body: str
    pos: tuple[float, float, float] = (0, 0, 0)
    wrap_radius: float = 0.0


class CableDef(BaseModel):
    id: str = ""
    spring_length: float = 0.3
    diameter: float = 0.002
    max_force: float = 500.0
    actuator_type: str = "motor"
    via_points: list[CableViaPoint] = Field(default_factory=list)
    # Hill-type params (when actuator_type == "muscle_hill")
    muscle_force: float = 0.0
    muscle_range: tuple[float, float] = (0.5, 1.5)
    muscle_lmin: float = 0.5
    muscle_lmax: float = 1.5
    muscle_fpmax: float = 1.0
    muscle_lengthrange: tuple[float, float] = (0.2, 0.4)


# ── Landmarks ─────────────────────────────────────────────────────────────


class LandmarkDef(BaseModel):
    name: str
    link: str
    offset: tuple[float, float, float] = (0, 0, 0)
    description: str = ""


# ── Exoskeleton components ────────────────────────────────────────────────


class CablePort(BaseModel):
    id: str
    type: str = "via"
    position: tuple[float, float, float] = (0, 0, 0)


class ExoPartDef(BaseModel):
    id: str
    part_type: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    attachment_link: str = ""
    attachment_offset: tuple[float, float, float] = (0, 0, 0)
    cable_ports: list[CablePort] = Field(default_factory=list)


class ExoAssemblyDef(BaseModel):
    name: str = ""
    version: str = "1.0"
    parts: list[ExoPartDef] = Field(default_factory=list)
    cables: list[CableDef] = Field(default_factory=list)


# ── Convenience: parse/serialize helpers ──────────────────────────────────


def to_json(model: BaseModel, **kwargs: Any) -> str:
    """Serialize a Melos model to JSON."""
    return model.model_dump_json(**kwargs)


def from_json(data: str | bytes, cls: type[BaseModel]) -> BaseModel:
    """Deserialize JSON to a Melos model."""
    return cls.model_validate_json(data)


def to_dict(model: BaseModel) -> dict[str, Any]:
    """Convert a Melos model to a plain dict."""
    return model.model_dump(mode="json")
