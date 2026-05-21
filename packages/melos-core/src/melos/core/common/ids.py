"""Identifier conventions for melos core models."""

from __future__ import annotations

import re
from typing import TypeAlias

Identifier: TypeAlias = str
ProjectId: TypeAlias = str
DeviceId: TypeAlias = str
SystemId: TypeAlias = str
AssemblyId: TypeAlias = str
AssetId: TypeAlias = str

BodyId: TypeAlias = str
LinkId: TypeAlias = str
JointId: TypeAlias = str
CoordinateId: TypeAlias = str
FrameId: TypeAlias = str
SiteId: TypeAlias = str
LandmarkId: TypeAlias = str
GeometryId: TypeAlias = str

SensorId: TypeAlias = str
ActuatorId: TypeAlias = str
InterfaceId: TypeAlias = str
AttachmentId: TypeAlias = str
ConnectionId: TypeAlias = str
CouplingId: TypeAlias = str
SignalId: TypeAlias = str

ContactGeometryId: TypeAlias = str
ContactPairId: TypeAlias = str


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")


def is_valid_identifier(value: str) -> bool:
    """Return ``True`` if ``value`` matches the project identifier pattern."""

    return bool(IDENTIFIER_PATTERN.fullmatch(value))


def require_valid_identifier(value: str, *, field_name: str = "id") -> str:
    """Validate an identifier and return it.

    The core model keeps identifier validation explicit rather than performing
    magic coercions during dataclass construction.
    """

    if not is_valid_identifier(value):
        raise ValueError(
            f"Invalid {field_name} {value!r}. IDs must start with a letter and "
            "contain only letters, digits, underscores, hyphens, or periods."
        )

    return value
