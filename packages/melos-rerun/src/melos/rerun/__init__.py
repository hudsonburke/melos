"""melos.rerun — Rerun component types and logging adapters.

This package defines custom PyArrow-backed components and archetypes that
supplement Rerun's built-in types with musculoskeletal-specific data.

Both Melos (Trame editor) and MoveDB (file importers) log to the same
component types and entity path conventions, enabling cross-project
SQL queries via Rerun's DuckDB extension.
"""

from .components import (
    JointDefinitionBatch,
    LinkDefinitionBatch,
    MuscleDefinitionBatch,
)
from .archetypes import Joint, Skeleton

__all__ = [
    "JointDefinitionBatch",
    "LinkDefinitionBatch",
    "MuscleDefinitionBatch",
    "Joint",
    "Skeleton",
]
