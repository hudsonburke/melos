"""melos.rerun — Canonical Arrow component types for biomechanics.

This package defines the shared Arrow schema (component batch types) that both
Melos (exoskeleton editor) and MoveDB (file importers) log to, enabling
cross-project SQL queries via Rerun's DuckDB extension.  Archetype/log helpers
were removed when no consumer used them; log directly with ``rerun`` built-ins
and these component batches.

Entity path conventions::

    {prefix}/subject                       — Subject (measurements)
    {prefix}/skeleton                      — Skeleton (joints + links summary)
    {prefix}/skeleton/links/{name}         — Link (Transform3D + LinkDefinition)
    {prefix}/skeleton/joints/{name}        — Joint (JointDefinition)
    {prefix}/skeleton/meshes/{link}/{name} — Mesh3D
    {prefix}/muscles/{name}                — MuscleDefinition
    {prefix}/actuators/{name}              — ActuatorDefinition
    {prefix}/cables/{name}/via-points/{id} — CableViaPoint
    {prefix}/assembly/{name}               — AssemblyConstraint
"""

from .components import (
    ActuatorDefinitionBatch,
    AssemblyConstraintBatch,
    BodyMeasurementsBatch,
    CableViaPointBatch,
    JointDefinitionBatch,
    LinkDefinitionBatch,
    MuscleDefinitionBatch,
)

__all__ = [
    "ActuatorDefinitionBatch",
    "AssemblyConstraintBatch",
    "BodyMeasurementsBatch",
    "CableViaPointBatch",
    "JointDefinitionBatch",
    "LinkDefinitionBatch",
    "MuscleDefinitionBatch",
]