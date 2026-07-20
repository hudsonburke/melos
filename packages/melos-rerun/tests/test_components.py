"""Tests for melos.rerun component types and archetypes.

These tests verify Arrow serialization without needing a Rerun viewer or
recording stream — they just exercise the ComponentBatchMixin protocol.
"""

from __future__ import annotations

import math

import pyarrow as pa

from melos.rerun.components import JointDefinitionBatch, LinkDefinitionBatch


class TestJointDefinitionBatch:
    def test_single_joint(self) -> None:
        data = [
            {
                "joint_type": "pin",
                "axis": [0.0, 0.0, 1.0],
                "limits": {"lower": -2.27, "upper": 0.0},
                "parent_link": "humerus",
                "child_link": "radius_ulna",
                "default_qpos": 0.0,
            }
        ]
        batch = JointDefinitionBatch(data)
        arr = batch.as_arrow_array()

        assert isinstance(arr, pa.StructArray)
        assert len(arr) == 1
        row = arr[0]
        assert row["joint_type"].as_py() == "pin"
        assert row["axis"].as_py() == [0.0, 0.0, 1.0]
        assert abs(row["limits"]["lower"].as_py() - (-2.27)) < 1e-6
        assert abs(row["limits"]["upper"].as_py() - 0.0) < 1e-6
        assert row["parent_link"].as_py() == "humerus"
        assert row["child_link"].as_py() == "radius_ulna"

    def test_multiple_joints(self) -> None:
        data = [
            {
                "joint_type": "pin",
                "axis": [0.0, 0.0, 1.0],
                "limits": {"lower": -2.27, "upper": 0.0},
                "parent_link": "humerus",
                "child_link": "radius_ulna",
                "default_qpos": 0.0,
            },
            {
                "joint_type": "universal",
                "axis": [0.0, 1.0, 0.0],
                "limits": {"lower": -1.57, "upper": 1.57},
                "parent_link": "scapula",
                "child_link": "humerus",
                "default_qpos": 0.0,
            },
        ]
        batch = JointDefinitionBatch(data)
        arr = batch.as_arrow_array()

        assert len(arr) == 2
        assert arr[0]["joint_type"].as_py() == "pin"
        assert arr[1]["joint_type"].as_py() == "universal"
        assert arr[1]["parent_link"].as_py() == "scapula"

    def test_unbounded_limits(self) -> None:
        data = [
            {
                "joint_type": "free",
                "axis": [0.0, 0.0, 0.0],
                "limits": {"lower": -math.inf, "upper": math.inf},
                "parent_link": "world",
                "child_link": "pelvis",
                "default_qpos": 0.0,
            }
        ]
        batch = JointDefinitionBatch(data)
        arr = batch.as_arrow_array()

        assert len(arr) == 1
        limits = arr[0]["limits"]
        assert math.isinf(limits["lower"].as_py())
        assert math.isinf(limits["upper"].as_py())


class TestLinkDefinitionBatch:
    def test_single_link(self) -> None:
        data = [
            {
                "name": "humerus",
                "mass": 1.8,
                "com": [0.0, 0.0, 0.15],
            }
        ]
        batch = LinkDefinitionBatch(data)
        arr = batch.as_arrow_array()

        assert isinstance(arr, pa.StructArray)
        assert len(arr) == 1
        row = arr[0]
        assert row["name"].as_py() == "humerus"
        assert abs(row["mass"].as_py() - 1.8) < 1e-6
        com = row["com"].as_py()
        assert len(com) == 3
        assert abs(com[0] - 0.0) < 1e-6
        assert abs(com[1] - 0.0) < 1e-6
        assert abs(com[2] - 0.15) < 1e-6
