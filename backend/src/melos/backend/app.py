"""FastAPI backend for the Melos design editor.

Serves skeleton state to the R3F frontend and accepts edits.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from melos.backend.models import (
    JointDef,
    JointLimits,
    JointPatch,
    LinkDef,
    LinkTransform,
    ModelState,
    SkeletonState,
    TransformPatch,
)

logger = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────────────────────

app = FastAPI(title="Melos Editor Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory state ────────────────────────────────────────────────────────

_model: ModelState | None = None


# ── Model loading ──────────────────────────────────────────────────────────


def load_model_from_osim(osim_path: str, prefix: str = "") -> ModelState:
    """Parse an OpenSim model and build a ModelState for the frontend."""
    import rerun as rr
    from melos.rerun.components import JointDefinitionBatch, LinkDefinitionBatch
    from rerun_importer_osim import parse_osim_model

    raw = parse_osim_model(osim_path)
    if raw is None:
        raise ValueError(f"Failed to parse OSIM model: {osim_path}")

    # ── Build joints dict ──────────────────────────────────────────────
    joints: dict[str, JointDef] = {}
    for j in raw.get("joints", []):
        coords = j.get("coordinates", [])
        first = coords[0] if coords else {}
        joints[j["name"]] = JointDef(
            joint_type=j.get("type", "CustomJoint"),
            axis=[0.0, 0.0, 1.0] if "Pin" in j.get("type", "") else [0.0, 0.0, 0.0],
            limits=JointLimits(
                lower=first.get("range", [-float("inf"), float("inf")])[0] if "range" in first else -float("inf"),
                upper=first.get("range", [-float("inf"), float("inf")])[1] if "range" in first else float("inf"),
            ),
            parent_link=j.get("parent", "ground"),
            child_link=j.get("child", ""),
            default_qpos=first.get("default", 0.0),
        )

    # ── Build links + transforms ──────────────────────────────────────
    links: dict[str, LinkDef] = {}
    transforms: dict[str, LinkTransform] = {}
    parent_map: dict[str, str] = {}

    for j in raw.get("joints", []):
        child = j.get("child", "")
        parent = j.get("parent", "ground")
        if child and parent:
            parent_map[child] = parent

    # Default ground transform
    transforms["ground"] = LinkTransform(
        translation=(0.0, 0.0, 0.0),
        rotation=(1.0, 0.0, 0.0, 0.0),
    )

    for b in raw.get("bodies", []):
        name = b["name"]
        loc = b.get("location", [0.0, 0.0, 0.0])
        orient = b.get("orientation", [0.0, 0.0, 0.0])
        # Convert Euler XYZ to quaternion (w, x, y, z)
        q = _euler_to_quat(*orient)
        transforms[name] = LinkTransform(
            translation=(float(loc[0]), float(loc[1]), float(loc[2])),
            rotation=q,
        )
        links[name] = LinkDef(
            name=name,
            mass=b.get("mass", 0.0),
            center_of_mass=list(b.get("mass_center", [0.0, 0.0, 0.0])),
            graphics_file=_first_mesh(b.get("geometry", [])),
        )

    return ModelState(
        name=raw.get("name", Path(osim_path).stem),
        skeleton=SkeletonState(
            joints=joints,
            links=links,
            transforms=transforms,
            parent_map=parent_map,
        ),
    )


def _euler_to_quat(x: float, y: float, z: float) -> tuple[float, float, float, float]:
    """Convert Euler XYZ (radians) to quaternion (w, x, y, z)."""
    cx, cy, cz = np.cos(np.array([x, y, z]) / 2)
    sx, sy, sz = np.sin(np.array([x, y, z]) / 2)
    return (
        float(cx * cy * cz + sx * sy * sz),  # w
        float(sx * cy * cz - cx * sy * sz),  # x
        float(cx * sy * cz + sx * cy * sz),  # y
        float(cx * cy * sz - sx * sy * cz),  # z
    )


def _first_mesh(geometry: list[dict]) -> str:
    """Extract first mesh filename from geometry list."""
    for g in geometry:
        f = g.get("file", "")
        if f:
            return f
    return ""


# ── Endpoints ──────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/model")
def get_model() -> ModelState:
    if _model is None:
        raise HTTPException(404, "No model loaded. POST /model/load first.")
    return _model


@app.post("/model/load")
def load_model(path: str) -> ModelState:
    """Load an OSIM model file into memory."""
    global _model
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise HTTPException(404, f"File not found: {resolved}")
    try:
        _model = load_model_from_osim(str(resolved))
        logger.info("Loaded model: %s", _model.name)
        return _model
    except Exception as e:
        raise HTTPException(400, f"Failed to load model: {e}")


@app.patch("/model/skeleton/joints/{joint_name}")
def patch_joint(joint_name: str, patch: JointPatch) -> JointDef:
    """Update a single joint definition."""
    if _model is None:
        raise HTTPException(404, "No model loaded.")
    skel = _model.skeleton
    if joint_name not in skel.joints:
        raise HTTPException(404, f"Joint not found: {joint_name}")
    joint = skel.joints[joint_name]
    if patch.joint_type is not None:
        joint.joint_type = patch.joint_type
    if patch.axis is not None:
        joint.axis = patch.axis
    if patch.limits is not None:
        joint.limits = patch.limits
    if patch.default_qpos is not None:
        joint.default_qpos = patch.default_qpos
    return joint


@app.patch("/model/skeleton/transforms/{link_name}")
def patch_transform(link_name: str, patch: TransformPatch) -> LinkTransform:
    """Update a link's spatial transform."""
    if _model is None:
        raise HTTPException(404, "No model loaded.")
    skel = _model.skeleton
    if link_name not in skel.transforms:
        raise HTTPException(404, f"Link not found: {link_name}")
    xform = skel.transforms[link_name]
    if patch.translation is not None:
        xform.translation = patch.translation
    if patch.rotation is not None:
        xform.rotation = patch.rotation
    return xform
