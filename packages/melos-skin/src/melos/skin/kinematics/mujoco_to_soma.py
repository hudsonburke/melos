"""Map MuJoCo joint coordinates to SOMA-X skeleton rotations.

Given MuJoCo coordinate values (joint angles), produces the corresponding
SOMA-X 77-joint axis-angle rotation tensor for driving ``SOMALayer.pose()``.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def build_mujoco_to_soma_mapping(
    anatomical_system: Any,
    translation_map: Any,
) -> dict[str, Any]:
    """Pre-compute the mapping from MuJoCo coordinates to SOMA-X joints.

    Returns a dict containing:
    - ``soma_joint_names``: list of 77 SOMA-X public joint names
    - ``mujoco_coord_ids``: list of MuJoCo coordinate IDs
    - ``projection_matrix``: (77, N_coords) matrix mapping MuJoCo angles to SOMA-X rotations
    - ``soma_joint_to_mujoco_link``: mapping from SOMA-X joint name to MuJoCo link ID

    The projection is linear: ``soma_rotations = projection_matrix @ mujoco_angles``.
    This works for small angles and gives a good approximation for the full range.
    """
    # Build link_id → joint correspondence from translation_map
    link_to_mhr_joint: dict[str, str] = {}
    for rule in getattr(translation_map, "rules", ()) or ():
        source_link_id = str(getattr(rule, "source_link_id", ""))
        target_ids = list(getattr(rule, "target_joint_ids", ()) or ())
        if source_link_id and target_ids:
            link_to_mhr_joint[source_link_id] = str(target_ids[0])

    # Collect all MuJoCo coordinates
    coord_ids: list[str] = []
    coord_axes: list[tuple[float, float, float]] = []
    coord_child_links: list[str] = []

    for joint in anatomical_system.joints:
        child_id = str(getattr(joint, "child_link_id", "") or "")
        for coord in getattr(joint, "coordinates", []) or []:
            coord_ids.append(coord.id)
            axis = tuple(coord.axis) if coord.axis else (1.0, 0.0, 0.0)
            coord_axes.append(axis)
            coord_child_links.append(child_id)

    n_coords = len(coord_ids)

    # Standard SOMA-X 77 joint names (order matters)
    soma_joint_names = [
        "Hips", "Spine1", "Spine2", "Chest",
        "Neck1", "Neck2", "Head", "HeadEnd", "Jaw", "LeftEye", "RightEye",
        # Left arm (11-38)
        "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
        "LeftHandThumb1", "LeftHandThumb2", "LeftHandThumb3", "LeftHandThumbEnd",
        "LeftHandIndex1", "LeftHandIndex2", "LeftHandIndex3", "LeftHandIndex4", "LeftHandIndexEnd",
        "LeftHandMiddle1", "LeftHandMiddle2", "LeftHandMiddle3", "LeftHandMiddle4", "LeftHandMiddleEnd",
        "LeftHandRing1", "LeftHandRing2", "LeftHandRing3", "LeftHandRing4", "LeftHandRingEnd",
        "LeftHandPinky1", "LeftHandPinky2", "LeftHandPinky3", "LeftHandPinky4", "LeftHandPinkyEnd",
        # Right arm (39-66)
        "RightShoulder", "RightArm", "RightForeArm", "RightHand",
        "RightHandThumb1", "RightHandThumb2", "RightHandThumb3", "RightHandThumbEnd",
        "RightHandIndex1", "RightHandIndex2", "RightHandIndex3", "RightHandIndex4", "RightHandIndexEnd",
        "RightHandMiddle1", "RightHandMiddle2", "RightHandMiddle3", "RightHandMiddle4", "RightHandMiddleEnd",
        "RightHandRing1", "RightHandRing2", "RightHandRing3", "RightHandRing4", "RightHandRingEnd",
        "RightHandPinky1", "RightHandPinky2", "RightHandPinky3", "RightHandPinky4", "RightHandPinkyEnd",
        # Left leg (67-71)
        "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "LeftToeEnd",
        # Right leg (72-76)
        "RightLeg", "RightShin", "RightFoot", "RightToeBase", "RightToeEnd",
    ]

    # Build SOMA-X joint name → MuJoCo link ID mapping
    soma_to_mujoco_link: dict[str, str] = {}
    # The translation_map maps MHR joint names to MuJoCo link IDs
    # SOMA-X joint names are the same as MHR joint names (minus Root)
    for soma_name in soma_joint_names:
        # Find the MuJoCo link that corresponds to this MHR joint
        for link_id, mhr_joint in link_to_mhr_joint.items():
            if mhr_joint == soma_name:
                soma_to_mujoco_link[soma_name] = link_id
                break

    # Build the projection matrix: (77_soma_joints, N_mujoco_coords)
    # For each SOMA-X joint, find the MuJoCo coordinate that rotates its parent link
    n_soma = len(soma_joint_names)
    projection = np.zeros((n_soma, n_coords), dtype=np.float64)

    # Build parent map from anatomical system
    parent_map: dict[str, str] = {}
    for joint in anatomical_system.joints:
        child_id = str(getattr(joint, "child_link_id", "") or "")
        parent_id = str(getattr(joint, "parent_link_id", "") or "")
        if child_id and parent_id:
            parent_map[child_id] = parent_id

    for soma_idx, soma_name in enumerate(soma_joint_names):
        mujoco_link = soma_to_mujoco_link.get(soma_name)
        if not mujoco_link:
            continue

        # Find the MuJoCo coordinate that controls this link's rotation
        # It's the coordinate of the joint whose child is this link
        for coord_idx, (coord_id, axis, child_link) in enumerate(
            zip(coord_ids, coord_axes, coord_child_links)
        ):
            if child_link == mujoco_link:
                # Project the MuJoCo rotation axis onto the SOMA-X rotation axis
                # For a direct correspondence, this is typically 1.0
                # For axis misalignment, it's the dot product
                projection[soma_idx, coord_idx] = 1.0
                break

    return {
        "soma_joint_names": soma_joint_names,
        "mujoco_coord_ids": coord_ids,
        "projection_matrix": projection,
        "soma_joint_to_mujoco_link": soma_to_mujoco_link,
        "link_to_mhr_joint": link_to_mhr_joint,
    }


def convert_mujoco_angles_to_soma_rotations(
    mujoco_coord_values: dict[str, float],
    mapping: dict[str, Any],
) -> np.ndarray:
    """Convert MuJoCo coordinate values to SOMA-X axis-angle rotations.

    Parameters
    ----------
    mujoco_coord_values :
        {coordinate_id: angle_in_radians} from MuJoCo FK.
    mapping :
        Pre-computed mapping from ``build_mujoco_to_soma_mapping()``.

    Returns
    -------
    np.ndarray
        (77, 3) axis-angle rotations for SOMA-X ``layer.pose()``.
    """
    coord_ids = mapping["mujoco_coord_ids"]
    projection = mapping["projection_matrix"]

    # Build angle vector
    angles = np.zeros(len(coord_ids), dtype=np.float64)
    for i, cid in enumerate(coord_ids):
        if cid in mujoco_coord_values:
            angles[i] = mujoco_coord_values[cid]

    # Project: (77, N) @ (N,) = (77,)
    # Each SOMA-X joint gets a scalar rotation from the projected MuJoCo angles
    scalar_rotations = projection @ angles  # (77,)

    # Convert scalar rotations to axis-angle (3,) per joint
    # For simplicity, use the primary rotation axis per SOMA-X joint
    # This is approximate — a full implementation would track the exact axis
    rotations = np.zeros((77, 3), dtype=np.float64)

    # Default rotation axes for SOMA-X joints (approximate)
    # These are the primary axes from the SOMA skeleton template
    soma_axes = _default_soma_rotation_axes()

    for i in range(77):
        axis = soma_axes[i]
        mag = scalar_rotations[i]
        rotations[i] = [axis[0] * mag, axis[1] * mag, axis[2] * mag]

    return rotations


def _default_soma_rotation_axes() -> list[tuple[float, float, float]]:
    """Default rotation axes for SOMA-X joints.

    These are approximate primary rotation axes from the SOMA skeleton template.
    A full implementation would load these from the template rig.
    """
    # Most joints rotate around the local X axis (forward axis in SOMA convention)
    default = [(1.0, 0.0, 0.0)] * 77

    # Spine/neck joints rotate around X (flexion/extension)
    for i in range(4):  # Hips, Spine1, Spine2, Chest
        default[i] = (1.0, 0.0, 0.0)

    # Shoulder joints have more complex axes
    # Left arm
    default[11] = (0.0, 0.0, 1.0)   # LeftShoulder - abduction
    default[12] = (1.0, 0.0, 0.0)   # LeftArm - rotation
    default[13] = (0.0, 0.0, 1.0)   # LeftForeArm - flexion
    # Right arm
    default[39] = (0.0, 0.0, -1.0)  # RightShoulder - abduction
    default[40] = (1.0, 0.0, 0.0)   # RightArm - rotation
    default[41] = (0.0, 0.0, -1.0)  # RightForeArm - flexion

    # Leg joints
    default[67] = (0.0, 0.0, 1.0)   # LeftLeg - flexion
    default[68] = (0.0, 0.0, 1.0)   # LeftShin - flexion
    default[72] = (0.0, 0.0, -1.0)  # RightLeg - flexion
    default[73] = (0.0, 0.0, -1.0)  # RightShin - flexion

    return default
