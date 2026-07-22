"""Generate a testable reference bundle from the SOMA neutral mesh.

This creates an NPZ file with the expected keys (joint_names, bind_pose, etc.)
that the Melos skin bundle loader expects.  Joint positions are computed from
the canonical mesh geometry rather than from the full SOMA layer.

Run once; the output NPZ lets the MHR adapter pipeline be tested without
the full SOMA-X or MHR model weights installed.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

# Load the SOMA neutral mesh
data = np.load("resources/third_party/skin/SOMA_neutral.npz", allow_pickle=True)
mean_verts = data["mean"]  # (18056, 3) float32
triangles = data["triangles"]  # (36108, 3) int32

# Define a minimal skeleton hierarchy matching a human body.
# Joint names follow the myofullbody / MHR convention.
# Each entry: (name, parent_index, vertex_landmark_indices_for_position)
# Joint positions are estimated by averaging nearby mesh vertices.
joint_defs = [
    # (name, parent_idx, list of vertex indices to average for position)
    ("pelvis",       -1, []),
    ("femur_r",       0, []),
    ("tibia_r",       1, []),
    ("talus_r",       2, []),
    ("calcn_r",       3, []),
    ("toes_r",        4, []),
    ("femur_l",       0, []),
    ("tibia_l",       6, []),
    ("talus_l",       7, []),
    ("calcn_l",       8, []),
    ("toes_l",        9, []),
    ("torso",         0, []),
    ("humerus_r",    11, []),
    ("ulna_r",       12, []),
    ("radius_r",     13, []),
    ("hand_r",       14, []),
    ("humerus_l",    11, []),
    ("ulna_l",       16, []),
    ("radius_l",     17, []),
    ("hand_l",       18, []),
]

n_joints = len(joint_defs)
joint_names = [j[0] for j in joint_defs]
joint_parent_ids = [j[1] for j in joint_defs]

# Compute joint positions from approximate anatomical landmarks on the mesh.
# We use known vertex index ranges from the segment_* arrays in the NPZ.
segment_data = {}
for key in data.keys():
    if key.startswith("segment_"):
        segment_data[key] = data[key]

# Torso: average of segment_torso vertices
torso_verts = mean_verts[data["segment_torso"]]
torso_center = torso_verts.mean(axis=0)
print(f"Torso center: {torso_center}")

# Pelvis: lowest part of torso, approximate from bounding box
pelvis_verts = mean_verts[data["segment_torso"]]
pelvis_bottom = pelvis_verts[:, 1].min()
pelvis_center = np.array([
    pelvis_verts[:, 0].mean(),
    pelvis_bottom,
    pelvis_verts[:, 2].mean(),
])
print(f"Pelvis center: {pelvis_center}")

# Head: from segment_head
head_verts = mean_verts[data["segment_head"]]
head_center = head_verts.mean(axis=0)
print(f"Head center: {head_center}")

# Feet: from segment_feet
feet_verts = mean_verts[data["segment_feet"]]
feet_bottom = feet_verts[:, 1].min()
feet_center = np.array([feet_verts[:, 0].mean(), feet_bottom, feet_verts[:, 2].mean()])
print(f"Feet center: {feet_center}")

# Compute joint positions as fraction-of-height between landmarks
ymin = pelvis_bottom  # ~0
ymax = feet_bottom    # ~negative (feet below pelvis in canonical pose)

# Actually the SOMA canonical pose might be in a different orientation.
# Let's just use the actual min/max of all vertices
all_verts = mean_verts
y_min = all_verts[:, 1].min()
y_max = all_verts[:, 1].max()
height = y_max - y_min
print(f"Height: {height:.2f} (y: {y_min:.2f} → {y_max:.2f})")

# Define joint positions as fractions of height from bottom
# These are approximate anatomical averages (in SOMA canonical frame)
joint_positions = [
    np.array([0.0, y_min + height * 0.52, 0.0]),   # pelvis
    np.array([0.06, y_min + height * 0.32, 0.06]),  # femur_r
    np.array([0.01, y_min + height * 0.16, 0.0]),   # tibia_r
    np.array([0.01, y_min + height * 0.04, 0.0]),   # talus_r
    np.array([-0.02, y_min, 0.0]),                   # calcn_r
    np.array([0.08, y_min + height * 0.01, 0.0]),   # toes_r
    np.array([-0.06, y_min + height * 0.32, -0.06]),# femur_l
    np.array([-0.01, y_min + height * 0.16, 0.0]),  # tibia_l
    np.array([-0.01, y_min + height * 0.04, 0.0]),  # talus_l
    np.array([0.02, y_min, 0.0]),                    # calcn_l
    np.array([-0.08, y_min + height * 0.01, 0.0]),  # toes_l
    np.array([0.0, y_min + height * 0.62, 0.0]),    # torso
    np.array([-0.12, y_min + height * 0.56, 0.08]), # humerus_r
    np.array([-0.10, y_min + height * 0.42, 0.06]), # ulna_r
    np.array([-0.10, y_min + height * 0.32, 0.05]), # radius_r
    np.array([-0.10, y_min + height * 0.22, 0.04]), # hand_r
    np.array([0.12, y_min + height * 0.56, -0.08]), # humerus_l
    np.array([0.10, y_min + height * 0.42, -0.06]), # ulna_l
    np.array([0.10, y_min + height * 0.32, -0.05]), # radius_l
    np.array([0.10, y_min + height * 0.22, -0.04]), # hand_l
]

# Build bind pose (4x4 transforms for each joint)
# Identity rotation, position from joint_positions
n = len(joint_names)
bind_pose_local = np.zeros((n, 4, 4), dtype=np.float32)
bind_pose_world = np.zeros((n, 4, 4), dtype=np.float32)

for i, pos in enumerate(joint_positions):
    bind_pose_world[i] = np.eye(4, dtype=np.float32)
    bind_pose_world[i, :3, 3] = pos

    if joint_parent_ids[i] >= 0:
        parent_world = bind_pose_world[joint_parent_ids[i]]
        parent_inv = np.linalg.inv(parent_world)
        bind_pose_local[i] = parent_inv @ bind_pose_world[i]
    else:
        bind_pose_local[i] = bind_pose_world[i].copy()

# Build simple skinning weights: each vertex assigned to nearest 3 joints
# (This is a simplification; real weights come from SOMA layer)
n_verts = len(mean_verts)
max_weights = 4
weight_data = []
weight_indices = []
weight_indptr = [0]

# Simple brute-force nearest-joint assignment (no scipy dependency)
joint_pos_array = np.array(joint_positions, dtype=np.float32)
max_weights = 4
weight_data = []
weight_indices = []
weight_indptr = [0]

for vi in range(n_verts):
    v = mean_verts[vi]
    # Compute distances to all joints
    diffs = joint_pos_array - v  # (n_joints, 3)
    dists = np.sqrt((diffs * diffs).sum(axis=1))
    # Get nearest max_weights joints
    idxs = np.argsort(dists)[:max_weights]
    nearest_dists = dists[idxs]
    weights = 1.0 / (nearest_dists + 1e-8)
    weights /= weights.sum()
    for w, idx in zip(weights, idxs):
        weight_data.append(float(w))
        weight_indices.append(int(idx))
    weight_indptr.append(len(weight_data))

# Save
output_path = Path("resources/third_party/skin/SOMA_neutral_reference.npz")
np.savez_compressed(
    output_path,
    joint_names=joint_names,
    joint_parent_ids=joint_parent_ids,
    bind_pose_world=bind_pose_world,
    bind_pose_local=bind_pose_local,
    skinning_weights_data=np.array(weight_data, dtype=np.float32),
    skinning_weights_indices=np.array(weight_indices, dtype=np.int32),
    skinning_weights_indptr=np.array(weight_indptr, dtype=np.int32),
    bind_shape=mean_verts,
    triangles=triangles,
)

print(f"\nSaved reference bundle to {output_path}")
print(f"  Joints: {len(joint_names)}")
print(f"  Vertices: {n_verts}")
print(f"  Triangles: {len(triangles)}")
print(f"  Skin weights: {len(weight_data)} entries, {len(weight_indptr)-1} vertices")
print("\nJoint positions (cm):")
for name, pos in zip(joint_names, joint_positions):
    cm = pos * 100
    print(f"  {name:15s} ({cm[0]:8.2f}, {cm[1]:8.2f}, {cm[2]:8.2f})")
