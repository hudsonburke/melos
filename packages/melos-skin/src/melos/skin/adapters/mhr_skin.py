from __future__ import annotations

import importlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from .skin_bundle import load_example_skin_reference_bundle


@lru_cache(maxsize=4)
def _load_mhr_somax_layer(data_root: str) -> tuple[Any, Any, Any]:
    importlib.invalidate_caches()

    import torch
    from soma import SOMALayer
    from soma.geometry.rig_utils import joint_world_to_local

    layer = SOMALayer(
        data_root=data_root,
        identity_model_type="mhr",
        device="cpu",
        mode="dense",
    )
    return layer, torch, joint_world_to_local


@lru_cache(maxsize=8)
def _build_cached_default_example_mhr_skin_bundle(
    data_root: str,
    global_scale: float,
) -> dict[str, Any] | None:
    return build_example_mhr_skin_bundle(
        Path(data_root),
        identity_coeffs=[],
        scale_params=[],
        global_scale=global_scale,
    )



def build_example_mhr_skin_bundle(
    data_root: Path | str,
    *,
    identity_coeffs: list[float] | None = None,
    scale_params: list[float] | None = None,
    global_scale: float = 1.0,
) -> dict[str, Any] | None:
    data_root_path = Path(data_root)

    if identity_coeffs is None and scale_params is None:
        return _build_cached_default_example_mhr_skin_bundle(str(data_root_path), float(global_scale))

    reference_bundle = load_example_skin_reference_bundle(data_root_path / "SOMA_neutral.npz")
    if reference_bundle is None:
        return None

    importlib.invalidate_caches()
    try:
        layer, torch, joint_world_to_local = _load_mhr_somax_layer(str(data_root_path))
    except ImportError:
        return None

    resolved_identity_coeffs = identity_coeffs or [0.0] * int(layer.identity_model.num_identity_coeffs)
    resolved_scale_params = scale_params or [0.0] * int(layer.identity_model.num_scale_params)

    if len(resolved_identity_coeffs) != int(layer.identity_model.num_identity_coeffs):
        raise ValueError(
            "identity_coeffs must match MHR identity dimension "
            f"({int(layer.identity_model.num_identity_coeffs)})"
        )
    if len(resolved_scale_params) != int(layer.identity_model.num_scale_params):
        raise ValueError(
            "scale_params must match MHR scale dimension "
            f"({int(layer.identity_model.num_scale_params)})"
        )

    identity_tensor = torch.tensor([resolved_identity_coeffs], dtype=torch.float32)
    scale_tensor = torch.tensor([resolved_scale_params], dtype=torch.float32)
    rest_shape_m = layer.identity_model(
        identity_tensor,
        scale_tensor,
        global_scale=global_scale,
    )
    bind_world_m = layer.skeleton_transfer.fit(rest_shape_m)[0]
    bind_local_m = joint_world_to_local(
        bind_world_m,
        list(reference_bundle["joint_parent_ids"]),
    )

    rest_shape_cm = rest_shape_m[0].detach().cpu().numpy() * 100.0
    bind_world_cm = bind_world_m.detach().cpu().numpy()
    bind_local_cm = bind_local_m.detach().cpu().numpy()
    bind_world_cm[:, :3, 3] *= 100.0
    bind_local_cm[:, :3, 3] *= 100.0

    joint_names = list(reference_bundle["joint_names"])
    joints = {
        joint_name: (
            float(bind_world_cm[index][0][3]),
            float(bind_world_cm[index][1][3]),
            float(bind_world_cm[index][2][3]),
        )
        for index, joint_name in enumerate(joint_names)
    }

    faces = layer.faces.detach().cpu().numpy().tolist()

    return {
        "asset_path": str(data_root_path / "MHR" / "base_body_lod1.obj"),
        "data_root": str(data_root_path),
        "source_model": "mhr",
        "identity_model_type": "mhr",
        "identity_coeffs": [float(value) for value in resolved_identity_coeffs],
        "scale_params": [float(value) for value in resolved_scale_params],
        "global_scale": float(global_scale),
        "vertices": [[float(x), float(y), float(z)] for x, y, z in rest_shape_cm],
        "faces": [[int(a), int(b), int(c)] for a, b, c in faces],
        "joint_names": joint_names,
        "joint_parent_ids": list(reference_bundle["joint_parent_ids"]),
        "joints": joints,
        "bind_pose_world": bind_world_cm.tolist(),
        "bind_pose_local": bind_local_cm.tolist(),
        "weight_data": list(reference_bundle["weight_data"]),
        "weight_indices": list(reference_bundle["weight_indices"]),
        "weight_indptr": list(reference_bundle["weight_indptr"]),
    }
