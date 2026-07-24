"""Blender integration for SOMA-X driven mesh deformation.

Provides a depsgraph handler that updates mesh vertices from SOMA-X
when MuJoCo coordinate values change on the armature.
"""

from __future__ import annotations

import importlib
from typing import Any

import numpy as np


def setup_soma_driver(
    mesh_obj: Any,
    arm_obj: Any,
    data_root: str,
    identity_coeffs: list[float] | None = None,
    scale_params: list[float] | None = None,
    rest_vertices: np.ndarray | None = None,
) -> dict[str, Any]:
    """Set up SOMA-X driven mesh deformation.

    Registers a depsgraph handler that re-deforms the mesh from SOMA-X
    whenever the armature's FK coordinate properties change.

    Parameters
    ----------
    mesh_obj :
        The Blender mesh object to deform.
    arm_obj :
        The armature object carrying FK coordinate custom properties.
    data_root :
        Path to SOMA-X data directory.
    identity_coeffs :
        MHR identity coefficients (45-dim).  Default zeros.
    scale_params :
        MHR scale parameters (68-dim).  Default zeros.
    rest_vertices :
        Pre-computed rest-pose vertices (V, 3) in metres.
        If None, computed from SOMA-X.

    Returns
    -------
    dict
        Metadata including handler reference for cleanup.
    """
    bpy = importlib.import_module("bpy")

    # Store driver state on the mesh object's custom properties
    mesh_obj["soma_driver_active"] = True
    mesh_obj["soma_data_root"] = data_root

    # Cache rest vertices on the mesh
    if rest_vertices is not None:
        mesh_obj["soma_rest_vertices"] = rest_vertices.tolist()
    else:
        mesh_obj["soma_rest_vertices"] = None

    # Store identity/scale for deferred init
    mesh_obj["soma_identity_coeffs"] = identity_coeffs or []
    mesh_obj["soma_scale_params"] = scale_params or []

    # Register depsgraph handler
    handler_name = f"_soma_driver_{mesh_obj.name}"

    def _update_handler(scene: Any, depsgraph: Any) -> None:
        """Update mesh vertices from SOMA-X when FK coords change."""
        _soma_update_mesh(mesh_obj.name)

    # Remove existing handler if any
    for h in list(bpy.app.handlers.depsgraph_update_post):
        if getattr(h, "__name__", "") == handler_name:
            bpy.app.handlers.depsgraph_update_post.remove(h)

    _update_handler.__name__ = handler_name
    bpy.app.handlers.depsgraph_update_post.append(_update_handler)

    return {
        "handler": _update_handler,
        "mesh_obj": mesh_obj,
        "arm_obj": arm_obj,
    }


def _soma_update_mesh(mesh_name: str) -> None:
    """Core update: read FK coords from armature, deform mesh via SOMA-X."""
    bpy = importlib.import_module("bpy")

    mesh_obj = bpy.data.objects.get(mesh_name)
    if mesh_obj is None:
        return

    if not mesh_obj.get("soma_driver_active"):
        return

    # Find the armature (parent or first armature modifier)
    arm_obj = None
    for mod in mesh_obj.modifiers:
        if mod.type == "ARMATURE" and mod.object is not None:
            arm_obj = mod.object
            break
    if arm_obj is None:
        return

    # Read FK coordinate values from armature custom properties
    fk_meta_str = arm_obj.get("melos_fk_system")
    if not fk_meta_str:
        return

    import json
    try:
        fk_meta = json.loads(fk_meta_str)
    except (json.JSONDecodeError, TypeError):
        return

    # Extract current coordinate values from custom properties
    coord_values: dict[str, float] = {}
    for entry in fk_meta.get("coordinates", []):
        prop_name = f"melos_fk_{entry['id']}"
        if hasattr(arm_obj, prop_name):
            coord_values[entry["id"]] = getattr(arm_obj, prop_name)

    # Skip update if all coords are zero (rest pose)
    if all(abs(v) < 1e-8 for v in coord_values.values()):
        return

    # Lazy-init the SOMA-X deformer
    deformer = _get_or_create_deformer(mesh_obj, arm_obj)
    if deformer is None:
        return

    # Get the mapping
    mapping = _get_or_create_mapping(arm_obj)

    # Deform via SOMA-X
    posed_vertices = deformer.pose_from_mujoco_angles(coord_values, mapping)

    # Apply to Blender mesh
    mesh_data = mesh_obj.data
    if len(mesh_data.vertices) != posed_vertices.shape[0]:
        return  # Vertex count mismatch

    for i, v in enumerate(mesh_data.vertices):
        v.co.x = float(posed_vertices[i, 0])
        v.co.y = float(posed_vertices[i, 1])
        v.co.z = float(posed_vertices[i, 2])

    mesh_data.update()


# Module-level caches
_deformer_cache: dict[str, Any] = {}
_mapping_cache: dict[str, Any] = {}


def _get_or_create_deformer(mesh_obj: Any, arm_obj: Any) -> Any:
    """Get or create the SOMA-X deformer for a mesh object."""
    key = mesh_obj.name
    if key in _deformer_cache:
        return _deformer_cache[key]

    try:
        from melos.skin.kinematics.soma_deformer import SOMADeformer
    except ImportError:
        return None

    data_root = mesh_obj.get("soma_data_root", "")
    if not data_root:
        return None

    identity_coeffs = mesh_obj.get("soma_identity_coeffs", [])
    scale_params = mesh_obj.get("soma_scale_params", [])

    try:
        deformer = SOMADeformer(data_root, identity_coeffs, scale_params)
        _deformer_cache[key] = deformer
        return deformer
    except Exception:
        return None


def _get_or_create_mapping(arm_obj: Any) -> Any:
    """Get or create the MuJoCo→SOMA-X mapping."""
    key = "default"
    if key in _mapping_cache:
        return _mapping_cache[key]

    try:
        from melos.skin.kinematics.mujoco_to_soma import build_mujoco_to_soma_mapping
        from melos.sim import import_mjcf
        from melos.skin.mappings.myofullbody_to_human_v1 import build_myofullbody_translation_map
        from pathlib import Path
    except ImportError:
        return None

    try:
        # Find the project XML path from the scene or use default
        project_path = Path("resources/third_party/myofullbody/body/myofullbody.xml")
        project = import_mjcf(str(project_path)).project
        anatomical = project.get_anatomical_system()
        tm = build_myofullbody_translation_map()
        mapping = build_mujoco_to_soma_mapping(anatomical, tm)
        _mapping_cache[key] = mapping
        return mapping
    except Exception:
        return None


def remove_soma_driver(mesh_obj: Any) -> None:
    """Remove the SOMA-X driver from a mesh object."""
    bpy = importlib.import_module("bpy")

    mesh_obj["soma_driver_active"] = False
    handler_name = f"_soma_driver_{mesh_obj.name}"

    for h in list(bpy.app.handlers.depsgraph_update_post):
        if getattr(h, "__name__", "") == handler_name:
            bpy.app.handlers.depsgraph_update_post.remove(h)

    _deformer_cache.pop(mesh_obj.name, None)


__all__ = ["setup_soma_driver", "remove_soma_driver"]
