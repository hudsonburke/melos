"""Pydantic models for the Melos backend API.

These mirror the Arrow component types from melos.rerun but serialized
as JSON for the R3F frontend.  They are the wire format contract.
"""

from __future__ import annotations

from pydantic import BaseModel


class JointLimits(BaseModel):
    lower: float = -float("inf")
    upper: float = float("inf")


class JointDef(BaseModel):
    joint_type: str
    axis: list[float]
    limits: JointLimits
    parent_link: str
    child_link: str
    default_qpos: float = 0.0


class LinkDef(BaseModel):
    name: str
    mass: float = 0.0
    center_of_mass: list[float] = [0.0, 0.0, 0.0]
    inertia: list[float] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    graphics_file: str = ""
    visible: bool = True


class LinkTransform(BaseModel):
    translation: tuple[float, float, float]
    rotation: tuple[float, float, float, float]  # (w, x, y, z)


class SkeletonState(BaseModel):
    joints: dict[str, JointDef]
    links: dict[str, LinkDef]
    transforms: dict[str, LinkTransform]
    parent_map: dict[str, str]


class ModelState(BaseModel):
    """The full model state returned by GET /model."""
    name: str
    skeleton: SkeletonState


class JointPatch(BaseModel):
    """Incoming edit for a single joint."""
    joint_type: str | None = None
    axis: list[float] | None = None
    limits: JointLimits | None = None
    default_qpos: float | None = None


class TransformPatch(BaseModel):
    """Incoming edit for a link transform."""
    translation: tuple[float, float, float] | None = None
    rotation: tuple[float, float, float, float] | None = None
