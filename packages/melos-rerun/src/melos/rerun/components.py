"""Custom Rerun component types for biomechanics and musculoskeletal simulation.

Canonical Arrow schemas shared between Melos (exoskeleton editor) and MoveDB
(file importers).  Both projects log to the same component types at compatible
entity paths so that cross-project SQL queries (via Rerun's DuckDB extension)
work transparently.

Each component class follows the ``rr.ComponentBatchMixin`` protocol.
"""

from __future__ import annotations

import math
from typing import Any

import pyarrow as pa

import rerun as rr

# ===========================================================================
# Arrow type constants  —  the canonical schema shared by all consumers
# ===========================================================================

# ── JointDefinition ────────────────────────────────────────────────────────
# Describes a single joint — type, axis, limits, parent/child links.
# Used by: OSIM importer (MoveDB), Melos editor, MuJoCo compiler.
JOINT_DEFINITION = pa.struct([
    ("joint_type", pa.utf8()),
    ("axis", pa.list_(pa.float32(), 3)),
    ("limits", pa.struct([
        ("lower", pa.float32()),
        ("upper", pa.float32()),
    ])),
    ("parent_link", pa.utf8()),
    ("child_link", pa.utf8()),
    ("default_qpos", pa.float32()),
])

# ── LinkDefinition ────────────────────────────────────────────────────────
# Inertial and display properties of a rigid link / body.
# Used by: OSIM importer (MoveDB), Melos editor, MuJoCo compiler.
LINK_DEFINITION = pa.struct([
    ("name", pa.utf8()),
    ("mass", pa.float32()),
    ("center_of_mass", pa.list_(pa.float32(), 3)),
    ("inertia", pa.list_(pa.float32(), 6)),         # [xx, yy, zz, xy, xz, yz]
    ("graphics_file", pa.utf8()),                    # mesh filename or URI
    ("visible", pa.bool_()),
])

# ── BodyMeasurements ──────────────────────────────────────────────────────
# Subject anthropometric measurements from C3D PROCESSING / SUBJECTS params.
# Used by: C3D importer (MoveDB), Melos scaling pipeline.
BODY_MEASUREMENTS = pa.struct([
    ("body_mass", pa.float32()),
    ("body_height", pa.float32()),
    ("segment", pa.utf8()),                          # e.g. "right_femur"
    ("length", pa.float32()),
    ("circumference", pa.float32()),
    ("width", pa.float32()),
    ("depth", pa.float32()),
])

# ── MuscleDefinition ──────────────────────────────────────────────────────
# A muscle path with via-point sites and physiological params.
#
# ``muscle_model`` discriminates the type of muscle model:
#   "hill" — Hill-type (default): max_force, optimal_fiber_length,
#            tendon_slack_length, pennation_angle.
#   Future values: "volumetric" (MRI-based 3D), "fem" (finite element),
#   "smpl" (SMPL-style body mesh), etc. may add different parameter fields.
#
# Used by: OSIM importer, Melos editor, MuJoCo compiler (hill → <muscle>).
MUSCLE_DEFINITION = pa.struct([
    ("name", pa.utf8()),
    ("muscle_model", pa.utf8()),                    # "hill", "volumetric", etc.
    ("site_ids", pa.list_(pa.utf8())),               # via-point path
    ("max_force", pa.float32()),                     # Hill-type: max isometric force (N)
    ("optimal_fiber_length", pa.float32()),           # Hill-type: optimal fiber length (m)
    ("tendon_slack_length", pa.float32()),            # Hill-type: tendon slack length (m)
    ("pennation_angle", pa.float32()),                # Hill-type: pennation angle (rad)
])

# ── ActuatorDefinition ────────────────────────────────────────────────────
# An actuator (motor, muscle equivalent, torque source) on a joint.
# Used by: Melos exoskeleton editor, MuJoCo compiler.
ACTUATOR_DEFINITION = pa.struct([
    ("name", pa.utf8()),
    ("actuator_type", pa.utf8()),                    # "motor", "muscle", "torque"
    ("joint_name", pa.utf8()),                       # which joint it acts on
    ("control_range", pa.struct([
        ("lower", pa.float32()),
        ("upper", pa.float32()),
    ])),
    ("optimal_force", pa.float32()),
    ("gear_ratio", pa.float32()),
])

# ── CableViaPoint ─────────────────────────────────────────────────────────
# A via-point or wrap surface for cable routing in exoskeleton design.
# Used by: Melos editor only (for now).
CABLE_VIA_POINT = pa.struct([
    ("cable_name", pa.utf8()),
    ("point_id", pa.utf8()),
    ("position", pa.list_(pa.float32(), 3)),          # in parent frame
    ("wrap_surface", pa.utf8()),                      # "" means free point
    ("parent_link", pa.utf8()),
    ("radius", pa.float32()),
])

# ── AssemblyConstraint ────────────────────────────────────────────────────
# How one system attaches to another (e.g. exo brace to skeleton link).
# Used by: Melos editor.
ASSEMBLY_CONSTRAINT = pa.struct([
    ("name", pa.utf8()),
    ("source_system", pa.utf8()),
    ("target_link", pa.utf8()),
    ("constraint_type", pa.utf8()),                   # "rigid", "welded", "revolute"
    ("transform", pa.struct([                         # source-in-target frame
        ("translation", pa.list_(pa.float32(), 3)),
        ("rotation", pa.list_(pa.float32(), 4)),       # (w, x, y, z)
    ])),
])

# ===========================================================================
# Component batches
# ===========================================================================


class JointDefinitionBatch(rr.ComponentBatchMixin):
    """Canonical joint definition with type, axis, limits, and reference links.

    Every joint in a logged model should include exactly one
    ``JointDefinitionBatch`` element at its entity path, enabling SQL queries
    like ``SELECT joint_type FROM joints WHERE joint_type = 'pin'`` across
    recordings from different source formats.
    """

    _ARROW_TYPE = JOINT_DEFINITION

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    def as_arrow_array(self) -> pa.Array:
        return pa.array(self.data, type=self._ARROW_TYPE)

    @classmethod
    def _unbounded(cls) -> dict[str, float]:
        return {"lower": -math.inf, "upper": math.inf}


class LinkDefinitionBatch(rr.ComponentBatchMixin):
    """Inertial and visual properties of a rigid link / body.

    Logged at ``{prefix}/skeleton/links/{name}`` alongside
    ``rr.Transform3D`` for the spatial transform.
    """

    _ARROW_TYPE = LINK_DEFINITION

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    def as_arrow_array(self) -> pa.Array:
        return pa.array(self.data, type=self._ARROW_TYPE)


class BodyMeasurementsBatch(rr.ComponentBatchMixin):
    """Subject anthropometrics from C3D or manual input.

    Logged as static data at ``{prefix}/subject/body_measurements``.
    Enables cross-subject queries: ``SELECT * WHERE body_mass > 70``.
    """

    _ARROW_TYPE = BODY_MEASUREMENTS

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    def as_arrow_array(self) -> pa.Array:
        return pa.array(self.data, type=self._ARROW_TYPE)


class MuscleDefinitionBatch(rr.ComponentBatchMixin):
    """A muscle path definition with via-point sites and physiology.

    ``muscle_model`` discriminates the type:
    - ``"hill"`` — Hill-type muscle with max_force, optimal_fiber_length,
      tendon_slack_length, pennation_angle (maps to MuJoCo ``<muscle>``).
    - Future types (``"volumetric"``, ``"fem"``, etc.) define their own
      parameter fields.
    """

    _ARROW_TYPE = MUSCLE_DEFINITION

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    def as_arrow_array(self) -> pa.Array:
        return pa.array(self.data, type=self._ARROW_TYPE)


class ActuatorDefinitionBatch(rr.ComponentBatchMixin):
    """An actuator (motor, muscle-equivalent, torque source) on a joint.

    ``actuator_type`` values:
    - ``"motor"`` — ideal torque/force source (MuJoCo ``<motor>``)
    - ``"muscle_hill"`` — Hill-type muscle actuator
    - ``"torque"`` — joint-level torque source

    Used by the MuJoCo compiler to generate actuator elements in MJCF.
    """

    _ARROW_TYPE = ACTUATOR_DEFINITION

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    def as_arrow_array(self) -> pa.Array:
        return pa.array(self.data, type=self._ARROW_TYPE)


class CableViaPointBatch(rr.ComponentBatchMixin):
    """A via-point or wrap surface on a cable path."""

    _ARROW_TYPE = CABLE_VIA_POINT

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    def as_arrow_array(self) -> pa.Array:
        return pa.array(self.data, type=self._ARROW_TYPE)


class AssemblyConstraintBatch(rr.ComponentBatchMixin):
    """Constraint between two systems (e.g. exo → skeleton)."""

    _ARROW_TYPE = ASSEMBLY_CONSTRAINT

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    def as_arrow_array(self) -> pa.Array:
        return pa.array(self.data, type=self._ARROW_TYPE)
