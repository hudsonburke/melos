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


