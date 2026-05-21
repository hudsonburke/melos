"""Enums owned by the contact subdomain."""

from __future__ import annotations

from enum import StrEnum


class ContactGeometryKind(StrEnum):
    """Geometric archetypes used to define contact surfaces."""

    SPHERE = "sphere"
    CAPSULE = "capsule"
    BOX = "box"
    CYLINDER = "cylinder"
    MESH = "mesh"
    PLANE = "plane"


class ContactFilterMode(StrEnum):
    """Whether a contact pair is included or excluded from simulation."""

    INCLUDE = "include"
    EXCLUDE = "exclude"
