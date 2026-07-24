"""FastAPI backend for the Melos design editor.

Serves skeleton state to the R3F frontend and accepts edits.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

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

    # ── Topological order & descendants ──────────────────────────────
    all_bodies = set()
    for name in links:
        all_bodies.add(name)
    for name in parent_map:
        all_bodies.add(name)
    # Ensure ground is always in the body set (used as root transform)
    if "ground" not in all_bodies:
        all_bodies.add("ground")

    children_of: dict[str, list[str]] = {}
    for child, parent in parent_map.items():
        children_of.setdefault(parent, []).append(child)

    order: list[str] = []
    visited: set[str] = set()
    roots = [b for b in all_bodies if b not in parent_map or parent_map.get(b) == "ground"]

    def topo_dfs(body: str) -> None:
        if body in visited:
            return
        visited.add(body)
        order.append(body)
        for child in children_of.get(body, []):
            topo_dfs(child)

    for root in sorted(roots):
        topo_dfs(root)

    # Add any unvisited bodies (orphans)
    for b in sorted(all_bodies):
        if b not in visited:
            order.append(b)

    # Descendants: for each body, collect all bodies in its subtree
    descendants: dict[str, list[str]] = {}
    # Process in reverse topological order so children are already computed
    for body in reversed(order):
        body_desc: set[str] = {body}
        for child in children_of.get(body, []):
            body_desc.update(descendants.get(child, {child}))
        descendants[body] = sorted(body_desc)

    # Default ground transform
    transforms["ground"] = LinkTransform(
        translation=(0.0, 0.0, 0.0),
        rotation=(1.0, 0.0, 0.0, 0.0),
    )

    # Build location/orientation map from joint data (stored per-joint, not per-body)
    joint_location: dict[str, list[float]] = {}
    joint_orientation: dict[str, list[float]] = {}
    for j in raw.get("joints", []):
        child = j.get("child", "")
        if "location" in j:
            joint_location[child] = j["location"]
        if "orientation" in j:
            joint_orientation[child] = j.get("orientation", [0.0, 0.0, 0.0])

    for b in raw.get("bodies", []):
        name = b["name"]
        loc = joint_location.get(name, b.get("location", [0.0, 0.0, 0.0]))
        orient = joint_orientation.get(name, b.get("orientation", [0.0, 0.0, 0.0]))
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
            order=order,
            descendants=descendants,
        ),
    )


def _euler_to_quat(x: float, y: float, z: float) -> tuple[float, float, float, float]:
    """Convert Euler XYZ (radians) to quaternion (w, x, y, z)."""
    cx, sx = math.cos(x / 2), math.sin(x / 2)
    cy, sy = math.cos(y / 2), math.sin(y / 2)
    cz, sz = math.cos(z / 2), math.sin(z / 2)
    return (
        cx * cy * cz + sx * sy * sz,  # w
        sx * cy * cz - cx * sy * sz,  # x
        cx * sy * cz + sx * cy * sz,  # y
        cx * cy * sz - sx * sy * cz,  # z
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


# ── Scaling endpoint ──────────────────────────────────────────────────────


from pydantic import BaseModel


class ScaleByLengthsRequest(BaseModel):
    target_lengths: dict[str, float]
    segment_to_link: dict[str, str | list[str]]
    target_mass: float | None = None


class ScaleByVectorsRequest(BaseModel):
    target_vectors: dict[str, list[float]]
    joint_to_link: dict[str, str]
    target_mass: float | None = None


from melos.backend.scaling import by_segment_lengths, by_bone_vectors, compute_bone_positions
from melos.backend.landmarks import LANDMARK_REGISTRY, landmark_world_positions


@app.post("/model/scale/lengths")
def scale_by_lengths(req: ScaleByLengthsRequest) -> dict:
    """Scale the loaded model using segment-length ratios."""
    if _model is None:
        raise HTTPException(404, "No model loaded.")
    report = by_segment_lengths(
        _model.skeleton,
        req.target_lengths,
        req.segment_to_link,
        target_mass=req.target_mass,
    )
    _model.skeleton = report.scaled_skeleton
    return {
        "link_scale_factors": report.link_scale_factors,
        "matched_segments": report.matched_segments,
        "unmatched_segments": report.unmatched_segments,
        "total_mass_before": report.total_mass_before,
        "total_mass_after": report.total_mass_after,
        "warnings": report.warnings,
    }


@app.post("/model/scale/vectors")
def scale_by_vectors(req: ScaleByVectorsRequest) -> dict:
    """Scale the loaded model using 3D bone vectors (MHR/SOMA skeleton fit)."""
    if _model is None:
        raise HTTPException(404, "No model loaded.")
    report = by_bone_vectors(
        _model.skeleton,
        {k: tuple(v) for k, v in req.target_vectors.items()},
        req.joint_to_link,
        target_mass=req.target_mass,
    )
    _model.skeleton = report.scaled_skeleton
    return {
        "link_scale_factors": report.link_scale_factors,
        "matched_segments": report.matched_segments,
        "unmatched_segments": report.unmatched_segments,
        "total_mass_before": report.total_mass_before,
        "total_mass_after": report.total_mass_after,
        "warnings": report.warnings,
    }


# ── Landmark endpoint ─────────────────────────────────────────────────────


@app.get("/model/marker-sets")
def list_marker_sets() -> dict:
    """List available marker sets (built-in YAML files)."""
    from melos.backend.marker_sets import available_marker_sets
    return available_marker_sets()


@app.get("/model/marker-sets/{set_name}")
def get_marker_set(set_name: str) -> dict:
    """Return a specific marker set by filename (without .yaml)."""
    from melos.backend.marker_sets import load_marker_set
    from melos.backend.marker_sets import builtin_marker_sets_dir
    path = builtin_marker_sets_dir() / f"{set_name}.yaml"
    if not path.exists():
        raise HTTPException(404, f"Marker set '{set_name}' not found")
    return load_marker_set(path)


@app.get("/model/landmarks")
def get_landmarks(set_name: str = "gait_full_body") -> dict:
    """Return landmark definitions with link-relative offsets for the frontend.

    The ``set_name`` parameter selects which YAML marker set to load.
    Default is ``gait_full_body`` (57 landmarks from the Rajagopal model).
    """
    from melos.backend.marker_sets import builtin_marker_sets_dir, load_marker_set

    if _model is None:
        raise HTTPException(404, "No model loaded.")

    # Load the marker set from YAML
    path = builtin_marker_sets_dir() / f"{set_name}.yaml"
    if not path.exists():
        raise HTTPException(404, f"Marker set '{set_name}' not found")
    marker_set = load_marker_set(path)

    # Compute world-space positions
    positions = landmark_world_positions(_model.skeleton)

    # Build response definitions
    definitions = {}
    for name, entry in marker_set.get("landmarks", {}).items():
        melos = entry.get("melos", {})
        definitions[name] = {
            "link": melos.get("link", ""),
            "offset": melos.get("offset", [0, 0, 0]),
            "desc": entry.get("description", ""),
            "wpos": positions.get(name, [0, 0, 0]),
        }

    return {
        "name": marker_set.get("name", set_name),
        "description": marker_set.get("description", ""),
        "landmarks": definitions,
        "count": len(definitions),
    }


# ── Landmark scaling endpoint ──────────────────────────────────────────────

from pydantic import BaseModel


class ScaleByLandmarksRequest(BaseModel):
    subject_measurements: dict[str, float]
    target_mass: float | None = None


@app.post("/model/scale/landmarks")
def scale_by_landmarks_endpoint(req: ScaleByLandmarksRequest):
    """Scale the loaded model using landmark-derived segment lengths."""
    from melos.backend.landmarks import landmark_world_positions
    from melos.backend.landmark_scaling import scale_by_landmarks
    if _model is None:
        raise HTTPException(404, "No model loaded.")
    lm_pos = landmark_world_positions(_model.skeleton)
    report = scale_by_landmarks(
        _model.skeleton,
        lm_pos,
        req.subject_measurements,
        target_mass=req.target_mass,
    )
    _model.skeleton = report.scaled_skeleton
    return {
        "link_scale_factors": report.link_scale_factors,
        "baseline_lengths": {},
        "matched_segments": report.matched_segments,
        "unmatched_segments": report.unmatched_segments,
        "total_mass_before": report.total_mass_before,
        "total_mass_after": report.total_mass_after,
        "warnings": report.warnings,
    }


# ── MHR adapter endpoint ──────────────────────────────────────────────────

from pydantic import BaseModel


class MHRFitRequest(BaseModel):
    identity_coeffs: list[float] | None = None
    scale_params: list[float] | None = None
    data_root: str | None = None
    target_mass: float | None = None


@app.post("/model/fit/mhr")
def fit_from_mhr(req: MHRFitRequest) -> dict:
    """Fit the skeleton to an MHR skin bundle.

    Takes MHR identity parameters (from SAM 3D Body video processing),
    loads the SOMA layer, extracts segment lengths, and scales the
    loaded skeleton to match.
    """
    from melos.backend.mhr_adapter import load_mhr_bundle, scale_skeleton_from_mhr

    if _model is None:
        raise HTTPException(404, "No model loaded.")

    bundle = load_mhr_bundle(
        identity_coeffs=req.identity_coeffs,
        scale_params=req.scale_params,
        data_root=req.data_root,
    )
    if bundle is None:
        raise HTTPException(500, "Failed to load MHR skin bundle (SOMA not available?)")

    result = scale_skeleton_from_mhr(
        _model.skeleton,
        bundle,
        target_mass=req.target_mass,
    )

    # Update the skeleton in place if scaling succeeded
    if result.get("scale_report"):
        from melos.backend.scaling import by_bone_vectors
        # Re-run scaling (already done in scale_skeleton_from_mhr, but
        # we need the updated skeleton state)
        joint_to_link = {
            "hip_r": "femur_r", "knee_r": "tibia_r",
            "hip_l": "femur_l", "knee_l": "tibia_l",
        }
        mhr_joints = bundle.get("joints", {})
        target_vectors = {}
        hip_r = mhr_joints.get("RightLeg")
        knee_r = mhr_joints.get("RightShin")
        if hip_r and knee_r:
            target_vectors["hip_r"] = (
                (knee_r[0] - hip_r[0]) / 100.0,
                (knee_r[1] - hip_r[1]) / 100.0,
                (knee_r[2] - hip_r[2]) / 100.0,
            )
        hip_l = mhr_joints.get("LeftLeg")
        knee_l = mhr_joints.get("LeftShin")
        if hip_l and knee_l:
            target_vectors["hip_l"] = (
                (knee_l[0] - hip_l[0]) / 100.0,
                (knee_l[1] - hip_l[1]) / 100.0,
                (knee_l[2] - hip_l[2]) / 100.0,
            )
        if target_vectors:
            from melos.backend.scaling import by_bone_vectors as scale_fn
            report = scale_fn(_model.skeleton, target_vectors, joint_to_link,
                              target_mass=req.target_mass)
            _model.skeleton = report.scaled_skeleton
            result["scale_report"] = {
                "link_scale_factors": report.link_scale_factors,
                "matched_segments": report.matched_segments,
                "total_mass_before": report.total_mass_before,
                "total_mass_after": report.total_mass_after,
            }

    return result


# ── Skin bundle endpoint ──────────────────────────────────────────────────


@app.get("/model/skin")
def get_skin_bundle() -> dict:
    """Return the MHR skin bundle data for frontend SkinnedMesh rendering.

    Returns vertices, faces, skin weights, joint hierarchy, and bind pose
    from the SOMA reference bundle.  The frontend uses this to render a
    skinned mesh overlaid on the skeleton.
    """
    from melos.skin.adapters.skin_bundle import load_example_skin_reference_bundle
    from pathlib import Path

    npz_path = Path("resources/third_party/skin/SOMA_neutral_reference.npz")
    if not npz_path.exists():
        raise HTTPException(404, f"Skin bundle not found. Run build_reference_bundle.py first.")

    bundle = load_example_skin_reference_bundle(npz_path)
    if bundle is None:
        raise HTTPException(500, "Failed to load skin bundle")

    # Convert numpy arrays to plain Python lists for JSON serialization
    def _to_list(val):
        if hasattr(val, "tolist"):
            return val.tolist()
        return val

    return {
        "vertices": [_to_list(v) for v in bundle["vertices"]],
        "faces": [_to_list(f) for f in bundle["faces"]],
        "joint_names": list(bundle["joint_names"]),
        "joint_parent_ids": [int(i) for i in bundle["joint_parent_ids"]],
        "joints": {k: [float(v) for v in val] for k, val in bundle["joints"].items()},
        "bind_pose_world": _to_list(bundle["bind_pose_world"]),
        "weight_data": [float(w) for w in bundle["weight_data"]],
        "weight_indices": [int(i) for i in bundle["weight_indices"]],
        "weight_indptr": [int(i) for i in bundle["weight_indptr"]],
        "n_verts": len(bundle["vertices"]),
        "n_faces": len(bundle["faces"]),
    }


# ── Assembly descriptor endpoints ─────────────────────────────────────────


@app.get("/model/assemblies")
def list_assemblies() -> dict:
    """List available exoskeleton assembly descriptors."""
    from melos.backend.assembly import list_assembly_descriptors
    from pathlib import Path
    desc_dir = Path("backend/src/melos/backend/descriptors")
    return {"assemblies": list_assembly_descriptors(desc_dir)}


@app.get("/model/assembly/{name}")
def resolve_assembly(name: str) -> dict:
    """Resolve an exoskeleton assembly against the current skeleton landmarks."""
    from melos.backend.assembly import load_assembly_descriptor, resolve_assembly
    from melos.backend.landmarks import landmark_world_positions
    from pathlib import Path

    if _model is None:
        raise HTTPException(404, "No model loaded.")

    desc_path = Path(f"backend/src/melos/backend/descriptors/{name}.yaml")
    if not desc_path.exists():
        raise HTTPException(404, f"Assembly descriptor '{name}' not found")

    descriptor = load_assembly_descriptor(desc_path)
    lm_pos = landmark_world_positions(_model.skeleton)
    lm_defs = {}
    from melos.backend.marker_sets import builtin_marker_sets_dir, load_marker_set
    ms_path = builtin_marker_sets_dir() / "gait_full_body.yaml"
    if ms_path.exists():
        ms = load_marker_set(ms_path)
        for k, v in ms.get("landmarks", {}).items():
            lm_defs[k] = v.get("melos", {})

    resolved = resolve_assembly(descriptor, lm_pos, lm_defs)
    return {"name": resolved["name"], "parts": resolved["parts"]}


# ── Assembly build endpoint ────────────────────────────────────────────────


from pydantic import BaseModel


class BuildAssemblyRequest(BaseModel):
    subject_overrides: dict[str, float] = {}
    """Optional subject-specific measurement overrides (metres)."""


@app.post("/model/assembly/{name}/build")
def build_assembly(name: str, req: BuildAssemblyRequest | None = None) -> dict:
    """Resolve an assembly descriptor and return the Proteus-ready spec.

    Returns the resolved part specifications that Proteus can consume
    directly — no Python coupling required.
    """
    from melos.backend.assembly import load_assembly_descriptor, resolve_assembly
    from melos.backend.landmarks import landmark_world_positions
    from pathlib import Path

    if _model is None:
        raise HTTPException(404, "No model loaded.")

    desc_path = Path(f"backend/src/melos/backend/descriptors/{name}.yaml")
    if not desc_path.exists():
        raise HTTPException(404, f"Assembly descriptor '{name}' not found")

    descriptor = load_assembly_descriptor(desc_path)
    lm_pos = landmark_world_positions(_model.skeleton)
    lm_defs = {}
    from melos.backend.marker_sets import builtin_marker_sets_dir, load_marker_set
    ms_path = builtin_marker_sets_dir() / "gait_full_body.yaml"
    if ms_path.exists():
        ms = load_marker_set(ms_path)
        for k, v in ms.get("landmarks", {}).items():
            lm_defs[k] = v.get("melos", {})

    subject_measurements = None
    if req and req.subject_overrides:
        subject_measurements = req.subject_overrides

    resolved = resolve_assembly(descriptor, lm_pos, lm_defs, subject_measurements)
    return {"name": resolved["name"], "version": descriptor.get("version", "1.0"), "parts": resolved["parts"]}


# ── MJCF compilation endpoint ─────────────────────────────────────────────


@app.get("/model/compile")
def compile_model() -> dict:
    """Compile the current Melos skeleton to MJCF XML."""
    from melos.backend.mjcf_compiler import compile_skeleton

    if _model is None:
        raise HTTPException(404, "No model loaded.")

    xml = compile_skeleton(_model.skeleton, _model.name)
    return {"mjcf": xml, "model": _model.name, "format": "mujoco_xml"}


# ── MJCF import endpoint ──────────────────────────────────────────────────


@app.post("/model/import/mjcf")
def import_mjcf(path: str) -> dict:
    """Import an MJCF model file into the Melos skeleton."""
    from melos.backend.mjcf_parser import parse_mjcf

    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise HTTPException(404, f"MJCF file not found: {resolved}")

    try:
        skeleton, cables = parse_mjcf(str(resolved))
    except Exception as e:
        raise HTTPException(400, f"Failed to parse MJCF: {e}")

    global _model
    _model = ModelState(
        name=resolved.stem,
        skeleton=skeleton,
    )

    return {
        "name": _model.name,
        "n_links": len(skeleton.links),
        "n_joints": len(skeleton.joints),
        "n_cables": len(cables),
    }


# ── Compile with assembly endpoint ────────────────────────────────────────


from pydantic import BaseModel


class CompileAssemblyRequest(BaseModel):
    assembly_name: str
    subject_overrides: dict[str, float] = {}


@app.post("/model/compile/with-assembly")
def compile_with_assembly(req: CompileAssemblyRequest) -> dict:
    """Load an assembly, apply it to the current skeleton, and compile to MJCF."""
    from melos.backend.assembly import load_assembly_descriptor, resolve_assembly
    from melos.backend.assembly_bridge import apply_assembly_to_skeleton
    from melos.backend.landmarks import landmark_world_positions
    from melos.backend.marker_sets import builtin_marker_sets_dir, load_marker_set
    from melos.backend.mjcf_compiler import compile_skeleton
    from pathlib import Path

    if _model is None:
        raise HTTPException(404, "No model loaded.")

    desc_path = Path(f"backend/src/melos/backend/descriptors/{req.assembly_name}.yaml")
    if not desc_path.exists():
        raise HTTPException(404, f"Assembly '{req.assembly_name}' not found")

    descriptor = load_assembly_descriptor(desc_path)
    lm_pos = landmark_world_positions(_model.skeleton)

    lm_defs = {}
    ms_path = builtin_marker_sets_dir() / "gait_full_body.yaml"
    if ms_path.exists():
        ms = load_marker_set(ms_path)
        for k, v in ms.get("landmarks", {}).items():
            lm_defs[k] = v.get("melos", {})

    resolved = resolve_assembly(descriptor, lm_pos, lm_defs,
                                subject_measurements=req.subject_overrides or None)

    combined, cables = apply_assembly_to_skeleton(
        _model.skeleton, resolved, landmark_positions=lm_pos,
    )

    xml = compile_skeleton(
        combined, f"{_model.name}_with_{req.assembly_name}",
        cables=cables,
    )

    return {"mjcf": xml, "model": _model.name, "assembly": req.assembly_name,
            "n_bodies": len(combined.links), "n_cables": len(cables),
            "format": "mujoco_xml"}
