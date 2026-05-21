from __future__ import annotations

from pathlib import Path
from typing import Any

from melos.core.retarget.measurements import compute_segment_measurements_from_rules
from melos.core.retarget.model import JointPositionSet, SegmentMeasurementSet


def build_example_skin_joint_set(skin_bundle: dict[str, Any]) -> JointPositionSet:
    return JointPositionSet(
        positions=dict(skin_bundle["joints"]),
        space="bind_pose_world",
        units="cm",
        annotations={"source": "melos.skin.adapters.skin_bundle"},
    )



def measure_example_skin_segments(
    skin_bundle: dict[str, Any],
    translation_map: Any,
) -> SegmentMeasurementSet:
    joint_set = build_example_skin_joint_set(skin_bundle)
    return compute_segment_measurements_from_rules(
        joint_set,
        getattr(translation_map, "rules", []),
        units=joint_set.units,
    )



def load_example_skin_reference_bundle(path: Path) -> dict[str, Any] | None:
    try:
        import numpy as np
    except ModuleNotFoundError:
        return None

    if not path.exists():
        return None

    data = np.load(path, allow_pickle=True)
    joint_names = [str(name) for name in data["joint_names"]]
    bind_pose_world = data["bind_pose_world"]
    joints = {
        name: (
            float(bind_pose_world[index][0][3]),
            float(bind_pose_world[index][1][3]),
            float(bind_pose_world[index][2][3]),
        )
        for index, name in enumerate(joint_names)
    }
    return {
        "asset_path": str(path),
        "data_root": str(path.parent),
        "vertices": [[float(x), float(y), float(z)] for x, y, z in data["bind_shape"]],
        "faces": [[int(a), int(b), int(c)] for a, b, c in data["triangles"]],
        "joint_names": joint_names,
        "joint_parent_ids": [int(value) for value in data["joint_parent_ids"]],
        "joints": joints,
        "bind_pose_world": data["bind_pose_world"],
        "bind_pose_local": data["bind_pose_local"],
        "weight_data": [float(value) for value in data["skinning_weights_data"]],
        "weight_indices": [int(value) for value in data["skinning_weights_indices"]],
        "weight_indptr": [int(value) for value in data["skinning_weights_indptr"]],
    }
