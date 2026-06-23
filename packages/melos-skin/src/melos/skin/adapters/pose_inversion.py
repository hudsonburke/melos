from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Any, Dict, Sequence, Tuple

import numpy as np

# Detect availability without importing heavy modules (lazy-friendly)
_torch_spec = importlib.util.find_spec("torch")
_soma_spec = importlib.util.find_spec("soma")

POSE_INVERSION_AVAILABLE: bool = (_torch_spec is not None and _soma_spec is not None)


def _get_layer_and_torch(data_root: str) -> Tuple[Any, Any]:
    """Load the SOMA layer and torch, falling back if procedural transforms are missing.

    First tries the shared cache in mhr_skin.py.  If that fails because
    ``SOMA_procedural_transforms.json`` is absent, creates a SOMALayer with
    procedural transforms disabled (legacy 78-joint rig).
    """
    import torch

    try:
        from .mhr_skin import _load_mhr_somax_layer
        layer, torch_mod, _ = _load_mhr_somax_layer(str(Path(data_root)))
        return layer, torch_mod
    except (FileNotFoundError, RuntimeError):
        pass

    # Fallback: create SOMALayer without procedural transforms
    from soma import SOMALayer

    layer = SOMALayer(
        data_root=str(data_root),
        identity_model_type="mhr",
        device="cpu",
        mode="dense",
        enable_procedural_transforms=False,
    )
    return layer, torch


def extract_skeleton_positions_from_mesh(
    vertices: np.ndarray,
    identity_coeffs: Sequence[float] | np.ndarray,
    scale_params: Sequence[float] | np.ndarray,
    data_root: str | Path,
) -> Dict[str, Tuple[float, float, float]]:
    """Extract SOMA skeleton joint positions (in meters) from a posed MHR mesh.

    Parameters
    ----------
    vertices
        Numpy array of posed mesh vertex positions with shape (V, 3). These are
        typically the MHR mesh vertices in centimeters; the function will detect
        likely-centimeter input and convert to meters automatically. If the
        coordinate magnitudes are small (< 10) they are assumed to already be
        in meters.
    identity_coeffs
        Identity coefficients for the MHR identity model (sequence-like or numpy
        array). Must match the identity dimension expected by the SOMA layer.
    scale_params
        Scale parameters for the MHR identity model (sequence-like or numpy
        array). Must match the scale param dimension expected by the SOMA layer.
    data_root
        Path to SOMA assets (the same data_root used elsewhere in this package).

    Returns
    -------
    Dict[str, Tuple[float, float, float]]
        Mapping from SOMA public joint name to (x, y, z) position in meters.

    Raises
    ------
    ImportError
        If required optional dependencies (torch, soma) are not available.
    ValueError
        If the vertices array has the wrong shape.
    """
    # Validate numpy array shape
    v = np.asarray(vertices, dtype=np.float32)
    if v.ndim != 2 or v.shape[1] != 3:
        raise ValueError("vertices must be a (V, 3) numpy array")

    # Quick availability check before attempting to load heavy modules
    if not POSE_INVERSION_AVAILABLE:
        # Attempt to provide a clearer ImportError by trying the loader once
        try:
            _get_layer_and_torch(str(data_root))
        except Exception as exc:  # pragma: no cover - environment-dependent
            raise ImportError(
                "SOMA and/or torch are not available; pose inversion cannot run. "
                "Install optional dependencies or check POSE_INVERSION_AVAILABLE."
            ) from exc

    # Load the cached SOMA layer and torch module
    layer, torch = _get_layer_and_torch(str(data_root))

    # Convert identity/scale params to torch tensors
    num_identity = int(getattr(layer.identity_model, "num_identity_coeffs", 45))
    num_scale = int(getattr(layer.identity_model, "num_scale_params", 68))

    if isinstance(identity_coeffs, torch.Tensor):
        identity_tensor = identity_coeffs.unsqueeze(0) if identity_coeffs.dim() == 1 else identity_coeffs
    else:
        id_list = list(map(float, identity_coeffs)) if identity_coeffs else [0.0] * num_identity
        identity_tensor = torch.tensor([id_list], dtype=torch.float32)

    if isinstance(scale_params, torch.Tensor):
        scale_tensor = scale_params.unsqueeze(0) if scale_params.dim() == 1 else scale_params
    else:
        sc_list = list(map(float, scale_params)) if scale_params else [0.0] * num_scale
        scale_tensor = torch.tensor([sc_list], dtype=torch.float32)


    # Detect units heuristically: if coordinates are large (e.g. human ~100), assume cm
    max_abs = float(np.max(np.abs(v))) if v.size else 0.0
    if max_abs > 10.0:
        # Likely centimeters -> convert to meters
        posed_m = v / 100.0
    else:
        posed_m = v.copy()

    # Build torch tensor (B, V, 3)
    posed_tensor = torch.tensor(posed_m, dtype=torch.float32).unsqueeze(0)

    # Lazy import of PoseInversion to avoid importing soma at module import time
    from soma.pose_inversion import PoseInversion

    inv = PoseInversion(layer, low_lod=False)
    inv.prepare_identity(identity_tensor, scale_tensor)
    result = inv.fit(posed_tensor)

    # result.rotations: (B, 78, 3, 3) — 78 joints including virtual Root at index 0
    # layer.pose() expects 77 non-Root joints in axis-angle (B, 77, 3) format
    rotations_78 = result.rotations[:, 1:, :, :]  # skip virtual Root → (B, 77, 3, 3)

    # Convert rotation matrices to axis-angle via Rodrigues inverse
    # R = I + sin(θ) K + (1-cos(θ)) K²  →  θ·axis from R
    trace = rotations_78[..., 0, 0] + rotations_78[..., 1, 1] + rotations_78[..., 2, 2]
    cos_angle = torch.clamp((trace - 1.0) / 2.0, -1.0, 1.0)
    angle = torch.acos(cos_angle).unsqueeze(-1)  # (B, 77, 1)
    axis = torch.stack([
        rotations_78[..., 2, 1] - rotations_78[..., 1, 2],
        rotations_78[..., 0, 2] - rotations_78[..., 2, 0],
        rotations_78[..., 1, 0] - rotations_78[..., 0, 1],
    ], dim=-1)  # (B, 77, 3)
    norm = torch.norm(axis, dim=-1, keepdim=True).clamp(min=1e-8)
    axis_angle = axis / norm * angle  # (B, 77, 3)

    pose_output = layer.pose(
        poses=axis_angle,
        transl=result.root_translation,
        pose2rot=True,
        absolute_pose=True,
        apply_correctives=False,
    )

    # pose_output is SOMAPoseOutput with .joints (B, 77, 3)
    joints_np = pose_output.joints[0].detach().cpu().numpy()

    # public_joint_names includes Root at index 0, but joints output
    # starts at Hips (77 joints).  Drop Root from names.
    joint_names = list(getattr(layer, "public_joint_names", []))
    if len(joint_names) == len(joints_np) + 1:
        joint_names = joint_names[1:]  # drop Root

    n_joints = min(len(joint_names), joints_np.shape[0])

    return {
        joint_names[i]: (float(joints_np[i, 0]), float(joints_np[i, 1]), float(joints_np[i, 2]))
        for i in range(n_joints)
    }
