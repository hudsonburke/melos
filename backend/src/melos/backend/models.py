"""Re-export canonical types from melos.core.model.

This module exists for backward compatibility.  All new code should
import directly from melos.core.model.
"""

from melos.core.model import (
    JointLimits,
    JointDef,
    LinkDef,
    LinkTransform,
    SkeletonState,
    ModelState,
    JointPatch,
    TransformPatch,
    CableDef,
    CableViaPoint,
    LandmarkDef,
    ExoPartDef,
    ExoAssemblyDef,
    CablePort,
)

__all__ = [
    "JointLimits", "JointDef", "LinkDef", "LinkTransform",
    "SkeletonState", "ModelState", "JointPatch", "TransformPatch",
    "CableDef", "CableViaPoint", "LandmarkDef",
    "ExoPartDef", "ExoAssemblyDef", "CablePort",
]
