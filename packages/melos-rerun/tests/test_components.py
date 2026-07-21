"""Tests for melos.rerun component types and archetypes.

Verifies Arrow serialization for all custom component types.
"""

from __future__ import annotations

import math

import pyarrow as pa

from melos.rerun.components import (
    ActuatorDefinitionBatch,
    AssemblyConstraintBatch,
    BodyMeasurementsBatch,
    CableViaPointBatch,
    JointDefinitionBatch,
    LinkDefinitionBatch,
    MuscleDefinitionBatch,
)


def _check_float32(val: float, expected: float, eps: float = 1e-6) -> None:
    assert abs(val - expected) < eps, f"{val} != {expected}"


class TestJointDefinitionBatch:
    def test_single_joint(self) -> None:
        data = [{
            "joint_type": "pin",
            "axis": [0.0, 0.0, 1.0],
            "limits": {"lower": -2.27, "upper": 0.0},
            "parent_link": "humerus",
            "child_link": "radius_ulna",
            "default_qpos": 0.0,
        }]
        batch = JointDefinitionBatch(data)
        arr = batch.as_arrow_array()

        assert isinstance(arr, pa.StructArray)
        assert len(arr) == 1
        row = arr[0]
        assert row["joint_type"].as_py() == "pin"
        assert row["axis"].as_py() == [0.0, 0.0, 1.0]
        _check_float32(row["limits"]["lower"].as_py(), -2.27)
        _check_float32(row["limits"]["upper"].as_py(), 0.0)
        assert row["parent_link"].as_py() == "humerus"
        assert row["child_link"].as_py() == "radius_ulna"

    def test_multiple_joints(self) -> None:
        data = [
            {"joint_type": "pin", "axis": [0, 0, 1],
             "limits": {"lower": -2.27, "upper": 0.0},
             "parent_link": "humerus", "child_link": "radius_ulna",
             "default_qpos": 0.0},
            {"joint_type": "CustomJoint", "axis": [0, 1, 0],
             "limits": {"lower": -1.57, "upper": 1.57},
             "parent_link": "scapula", "child_link": "humerus",
             "default_qpos": 0.0},
        ]
        batch = JointDefinitionBatch(data)
        arr = batch.as_arrow_array()
        assert len(arr) == 2
        assert arr[0]["joint_type"].as_py() == "pin"
        assert arr[1]["joint_type"].as_py() == "CustomJoint"

    def test_unbounded_limits(self) -> None:
        data = [{
            "joint_type": "free", "axis": [0, 0, 0],
            "limits": {"lower": -math.inf, "upper": math.inf},
            "parent_link": "world", "child_link": "pelvis",
            "default_qpos": 0.0,
        }]
        arr = JointDefinitionBatch(data).as_arrow_array()
        limits = arr[0]["limits"]
        assert math.isinf(limits["lower"].as_py())
        assert math.isinf(limits["upper"].as_py())


class TestLinkDefinitionBatch:
    def test_basic(self) -> None:
        data = [{
            "name": "humerus", "mass": 1.8,
            "center_of_mass": [0.0, 0.0, 0.15],
            "inertia": [0.01, 0.02, 0.03, 0.0, 0.0, 0.0],
            "graphics_file": "humerus.vtp",
            "visible": True,
        }]
        arr = LinkDefinitionBatch(data).as_arrow_array()
        assert len(arr) == 1
        row = arr[0]
        assert row["name"].as_py() == "humerus"
        _check_float32(row["mass"].as_py(), 1.8)
        com = row["center_of_mass"].as_py()
        _check_float32(com[2], 0.15)
        assert row["graphics_file"].as_py() == "humerus.vtp"
        assert row["visible"].as_py() is True


class TestBodyMeasurementsBatch:
    def test_basic(self) -> None:
        data = [
            {"body_mass": 75.0, "body_height": 1.80,
             "segment": "", "length": 0.0,
             "circumference": 0.0, "width": 0.0, "depth": 0.0},
            {"body_mass": 0.0, "body_height": 0.0,
             "segment": "right_femur", "length": 0.45,
             "circumference": 0.35, "width": 0.0, "depth": 0.0},
        ]
        arr = BodyMeasurementsBatch(data).as_arrow_array()
        assert len(arr) == 2
        _check_float32(arr[0]["body_mass"].as_py(), 75.0)
        assert arr[1]["segment"].as_py() == "right_femur"
        _check_float32(arr[1]["length"].as_py(), 0.45)


class TestMuscleDefinitionBatch:
    def test_basic(self) -> None:
        data = [{
            "name": "biceps",
            "muscle_model": "hill",
            "site_ids": ["origin", "midpoint", "insertion"],
            "max_force": 2000.0,
            "optimal_fiber_length": 0.08,
            "tendon_slack_length": 0.02,
            "pennation_angle": 0.17,
        }]
        arr = MuscleDefinitionBatch(data).as_arrow_array()
        assert arr[0]["name"].as_py() == "biceps"
        assert arr[0]["muscle_model"].as_py() == "hill"
        assert arr[0]["site_ids"].as_py() == ["origin", "midpoint", "insertion"]


class TestActuatorDefinitionBatch:
    def test_basic(self) -> None:
        data = [{
            "name": "elbow_motor",
            "actuator_type": "motor",
            "joint_name": "r_elbow",
            "control_range": {"lower": -100.0, "upper": 100.0},
            "optimal_force": 200.0,
            "gear_ratio": 1.5,
        }]
        arr = ActuatorDefinitionBatch(data).as_arrow_array()
        assert arr[0]["actuator_type"].as_py() == "motor"


class TestCableViaPointBatch:
    def test_basic(self) -> None:
        data = [{
            "cable_name": "finger_flexor",
            "point_id": "vp_01",
            "position": [0.01, 0.02, 0.03],
            "wrap_surface": "",
            "parent_link": "proximal_phalanx",
            "radius": 0.005,
        }]
        arr = CableViaPointBatch(data).as_arrow_array()
        assert arr[0]["cable_name"].as_py() == "finger_flexor"


class TestAssemblyConstraintBatch:
    def test_basic(self) -> None:
        data = [{
            "name": "forearm_brace",
            "source_system": "exo_arm",
            "target_link": "radius_ulna",
            "constraint_type": "rigid",
            "transform": {
                "translation": [0.0, 0.0, 0.1],
                "rotation": [1.0, 0.0, 0.0, 0.0],
            },
        }]
        arr = AssemblyConstraintBatch(data).as_arrow_array()
        assert arr[0]["constraint_type"].as_py() == "rigid"
