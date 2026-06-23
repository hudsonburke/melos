"""Inter-system enums used by project-level models."""

from __future__ import annotations

from enum import StrEnum


class InterfaceKind(StrEnum):
    """Semantic interface categories used to connect systems."""

    CUFF = "cuff"
    FOOTPLATE = "footplate"
    HARNESS = "harness"
    SOCKET = "socket"
    SOFT_TISSUE_REGION = "soft_tissue_region"
    BONE_ANCHOR_REGION = "bone_anchor_region"
    HAND_GRIP = "hand_grip"
    SKIN = "skin"
    CUSTOM = "custom"


class ConnectionKind(StrEnum):
    """Kinds of assembly connections between system interfaces."""

    RIGID = "rigid"
    COMPLIANT = "compliant"
    CONTACT_ONLY = "contact_only"
    OBSERVATIONAL = "observational"
    ALIGNMENT_ONLY = "alignment_only"


class ConstraintPolicy(StrEnum):
    """Constraint resolution policies for assembly connections."""

    LOWER_TO_WELD = "lower_to_weld"
    LOWER_TO_SPRINGS = "lower_to_springs"
    UPPER_TO_WELD = "upper_to_weld"
    UPPER_TO_SPRINGS = "upper_to_springs"


class AssetRole(StrEnum):
    """Intended purpose of an asset in the authoring or simulation pipeline."""

    IMAGING = "imaging"
    SEGMENTATION = "segmentation"
    VISUAL = "visual"
    COLLISION = "collision"
    SIMULATION = "simulation"
    FITTING = "fitting"
    ANALYSIS = "analysis"
