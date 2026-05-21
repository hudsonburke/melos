"""Project metadata and provenance primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias


AnnotationMap: TypeAlias = dict[str, str]


@dataclass(slots=True, kw_only=True)
class ProvenanceRecord:
    """Structured provenance attached to model entities or assets."""

    label: str = ""
    source_uri: str | None = None
    generated_by: str | None = None
    notes: str = ""
    annotations: AnnotationMap = field(default_factory=dict)
