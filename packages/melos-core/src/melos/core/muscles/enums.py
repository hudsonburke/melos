"""Enums owned by the muscle subdomain."""

from __future__ import annotations

from enum import StrEnum


class MusclePathPointKind(StrEnum):
    """Kinds of ordered points that define a muscle path."""

    ORIGIN = "origin"
    VIA = "via"
    INSERTION = "insertion"


class WrapGeometryKind(StrEnum):
    """Geometric archetypes used to influence muscle paths."""

    CYLINDER = "cylinder"
    SPHERE = "sphere"
    ELLIPSOID = "ellipsoid"
    TORUS = "torus"
    MESH = "mesh"
    CUSTOM = "custom"


class MuscleLineOfActionSource(StrEnum):
    """How a canonical muscle line of action is derived."""

    PATH_POINTS = "path_points"
    ASSOCIATED_MESH = "associated_mesh"
    CENTERLINE_ASSET = "centerline_asset"
    CUSTOM = "custom"


class MuscleRepresentationKind(StrEnum):
    """Preferred simulation or visualization representation for a muscle."""

    PATH = "path"
    VOLUMETRIC = "volumetric"
    HYBRID = "hybrid"
