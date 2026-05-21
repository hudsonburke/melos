"""Contact domain model definitions for melos core."""

from melos.core.contact.enums import ContactFilterMode, ContactGeometryKind
from melos.core.contact.model import ContactGeometry, ContactPair

__all__ = [
    "ContactFilterMode",
    "ContactGeometry",
    "ContactGeometryKind",
    "ContactPair",
]
