"""Shared kinematics concepts for melos core."""

from melos.core.system.enums import JointKind, CoordinateKind
from melos.core.system.model import CoordinateDefinition

__all__ = [
    "CoordinateDefinition",
    "CoordinateKind",
    "JointKind",
]
