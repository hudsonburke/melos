"""Custom Rerun component types for musculoskeletal simulation models.

Defines PyArrow-backed components that both Melos (editor) and MoveDB (importers)
log to consistent entity paths, enabling cross-project SQL queries via DuckDB.

Each component follows the ``rr.ComponentBatchMixin`` protocol and represents
a domain-specific data type not covered by Rerun's built-in archetypes.
"""

from __future__ import annotations

import math
from typing import Any

import pyarrow as pa

import rerun as rr

# ---------------------------------------------------------------------------
# Shared Arrow schemas (type-level constants, not instances)
# ---------------------------------------------------------------------------

JOINT_DEFINITION_TYPE = pa.struct([
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


# ---------------------------------------------------------------------------
# Component batches
# ---------------------------------------------------------------------------


class JointDefinitionBatch(rr.ComponentBatchMixin):
    """A batch of joint definitions at a single entity path.

    Each element describes one joint: its type, rotation axis in the parent
    frame, position limits, and which links it connects.

    Usage::

        batch = JointDefinitionBatch([
            {
                "joint_type": "pin",
                "axis": [0.0, 0.0, 1.0],
                "limits": {"lower": -2.27, "upper": 0.0},
                "parent_link": "humerus",
                "child_link": "radius_ulna",
                "default_qpos": 0.0,
            },
        ])

        rr.log("model/joints/r_elbow", batch)
    """

    _ARROW_TYPE = JOINT_DEFINITION_TYPE

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    def as_arrow_array(self) -> pa.Array:
        return pa.array(self.data, type=self._ARROW_TYPE)

    @classmethod
    def _limits_sentinel(cls) -> dict[str, float]:
        """Return a limits dict representing 'unbounded'."""
        return {"lower": -math.inf, "upper": math.inf}


class LinkDefinitionBatch(rr.ComponentBatchMixin):
    """Metadata about a rigid link/body: name, mass, center of mass."""

    _ARROW_TYPE = pa.struct([
        ("name", pa.utf8()),
        ("mass", pa.float32()),
        ("com", pa.list_(pa.float32(), 3)),
    ])

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    def as_arrow_array(self) -> pa.Array:
        return pa.array(self.data, type=self._ARROW_TYPE)


class MuscleDefinitionBatch(rr.ComponentBatchMixin):
    """A muscle via-point path through a series of attachment sites."""

    _ARROW_TYPE = pa.struct([
        ("name", pa.utf8()),
        ("site_ids", pa.list_(pa.utf8())),
        ("max_force", pa.float32()),
        ("optimal_length", pa.float32()),
        ("tendon_slack_length", pa.float32()),
        ("pennation_angle", pa.float32()),
    ])

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    def as_arrow_array(self) -> pa.Array:
        return pa.array(self.data, type=self._ARROW_TYPE)
