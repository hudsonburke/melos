#!/usr/bin/env python3
"""Headless exoskeleton cable-routing workflow.

Imports the MyoFullBody musculoskeletal model, adds a cable-driven
knee-assist exoskeleton device, and compiles back to MuJoCo MJCF.

Usage:
    python scripts/exoskeleton_cable_workflow.py [--with-skin] [--output-dir OUTPUT_DIR]

The --with-skin flag requires the MHR runtime (py-soma-x + torch).
Without it the script produces a complete cable-assisted MJCF model
using the anatomical skeleton only.
"""

from __future__ import annotations

import argparse
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

from melos.core.common.types import Transform
from melos.core.system.enums import CoordinateKind, JointKind
from melos.core.project.model import Project
from melos.core.system import (
    Actuator,
    ActuatorKind,
    CableParameters,
    Geometry,
    Joint,
    Link,
    RouteNode,
    RouteNodeKind,
    Site,
    SystemModel,
    SystemRole,
)
from melos.core.system.enums import GeometryRole
from melos.sim import compile_project
from melos.sim.mujoco.importers import import_mjcf


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MYO_FULLBODY_XML = _REPO_ROOT / "resources" / "third_party" / "myofullbody" / "body" / "myofullbody.xml"
_SKIN_ASSET_DIR = _REPO_ROOT / "resources" / "third_party" / "skin"


def _find_site_on_link(system: SystemModel, link_id: str, substring: str) -> str | None:
    """Return the first site id on *link_id* whose id contains *substring*."""
    for site in system.sites:
        if site.link_id == link_id and substring in site.id:
            return site.id
    return None


# ---------------------------------------------------------------------------
# Cable exoskeleton device builder
# ---------------------------------------------------------------------------

def build_knee_assist_exoskeleton(anatomical: SystemModel) -> SystemModel:
    """Create a cable-driven knee-assist exoskeleton device.

    The device has:
    - A hip anchor link attached near the pelvis
    - A knee pulley wrap geometry on the femur
    - A single cable running: hip_anchor → femur_pulley → tibia_insertion

    The cable is modelled as a MuJoCo spatial tendon with a motor actuator,
    providing assistive torque about the knee extension axis.
    """

    # Pick anatomical landmarks.
    # Use existing muscle sites on the right leg for anchor/insertion.
    anchor_site_id = _find_site_on_link(anatomical, "sacrum", "rect_abd_r") or "rect_abd_r_rect_abd_r-P1"
    insertion_site_id = _find_site_on_link(anatomical, "tibia_r", "knee_r") or "knee_r"

    # Create device links.
    hip_anchor = Link(
        id="exo_hip_anchor",
        name="Exo Hip Anchor",
        transform=Transform(translation=(0.0, 0.0, 0.0), rotation=(1.0, 0.0, 0.0, 0.0)),
    )
    thigh_cuff = Link(
        id="exo_thigh_cuff",
        name="Exo Thigh Cuff",
        transform=Transform(translation=(0.0, -0.2, 0.0), rotation=(1.0, 0.0, 0.0, 0.0)),
    )
    shank_cuff = Link(
        id="exo_shank_cuff",
        name="Exo Shank Cuff",
        transform=Transform(translation=(0.0, -0.2, 0.0), rotation=(1.0, 0.0, 0.0, 0.0)),
    )

    # Device sites: knee pulley for cable wrap, side site for wrap direction.
    knee_pulley = Site(
        id="exo_knee_pulley",
        name="Knee Pulley",
        link_id="exo_thigh_cuff",
        transform=Transform(translation=(0.0, 0.0, 0.02), rotation=(1.0, 0.0, 0.0, 0.0)),
    )
    knee_pulley_side = Site(
        id="exo_knee_pulley_side",
        name="Knee Pulley Side",
        link_id="exo_thigh_cuff",
        transform=Transform(translation=(0.05, 0.0, 0.0), rotation=(1.0, 0.0, 0.0, 0.0)),
    )

    # Cable actuator: runs from pelvis anchor, wraps around knee pulley, inserts at tibia.
    knee_cable = Actuator(
        id="knee_assist_cable",
        name="Knee Assist Cable",
        kind=ActuatorKind.CABLE,
        route=[
            RouteNode(kind=RouteNodeKind.SITE, site_id=anchor_site_id),
            RouteNode(
                kind=RouteNodeKind.WRAP,
                geometry_id="exo_knee_pulley",
                side_site_id="exo_knee_pulley_side",
            ),
            RouteNode(kind=RouteNodeKind.SITE, site_id=insertion_site_id),
        ],
        cable=CableParameters(
            stiffness=1500.0,
            damping=3.0,
            rest_length=0.3,
        ),
    )

    # Motor actuator driving the cable tendon (force-controlled).
    cable_motor = Actuator(
        id="knee_assist_motor",
        name="Knee Assist Motor",
        kind=ActuatorKind.MOTOR,
        joint_id=None,
    )

    # Wrap geometry for the knee pulley (sphere approximating a pulley).

    knee_wrap_geom = Geometry(
        id="exo_knee_pulley",
        name="Knee Pulley Wrap",
        kind="sphere",
        link_id="exo_thigh_cuff",
        site_id="exo_knee_pulley",
        role=GeometryRole.WRAP,
        parameters={"radius": 0.02},
    )
    # Joints connecting device links into a kinematic chain.

    hip_to_thigh = Joint(
        id="exo_hip_thigh_joint",
        name="Hip to Thigh",
        kind=JointKind.FIXED,
        parent_link_id="exo_hip_anchor",
        child_link_id="exo_thigh_cuff",
    )
    thigh_to_shank = Joint(
        id="exo_thigh_shank_joint",
        name="Thigh to Shank",
        kind=JointKind.FIXED,
        parent_link_id="exo_thigh_cuff",
        child_link_id="exo_shank_cuff",
    )

    device = SystemModel(
        id="cable_exo",
        name="Cable-Driven Knee Exoskeleton",
        role=SystemRole.DEVICE,
        root_link_id="exo_hip_anchor",
        links=[hip_anchor, thigh_cuff, shank_cuff],
        sites=[knee_pulley, knee_pulley_side],
        joints=[hip_to_thigh, thigh_to_shank],
        geometries=[knee_wrap_geom],
        actuators=[knee_cable, cable_motor],
    )

    return device


def build_elbow_assist_exoskeleton(anatomical: SystemModel) -> SystemModel:
    """Create a cable-driven elbow-flexion assist exoskeleton device.

    The device has:
    - An upper-arm anchor link attached near the proximal humerus
    - An elbow pulley wrap geometry on a cuff link at the distal humerus
    - A single cable running: humerus_anchor → elbow_pulley → radius_insertion

    The cable is modelled as a MuJoCo spatial tendon with a motor actuator,
    providing assistive torque about the elbow flexion axis (hinge).
    """

    # Pick anatomical landmarks.
    # Anchor: proximal anterior humerus (near deltoid insertion)
    anchor_site_id = _find_site_on_link(anatomical, "humerus_r", "DELT1_DELT1-P2") or "DELT1_DELT1-P2"
    # Insertion: radial tuberosity (biceps insertion)
    insertion_site_id = _find_site_on_link(anatomical, "radius_r", "BICshort_BICshort-P6") or "BICshort_BICshort-P6"

    # Create device links.
    upper_arm_anchor = Link(
        id="exo_elbow_upper_anchor",
        name="Exo Elbow Upper Anchor",
        transform=Transform(translation=(0.0, 0.0, 0.0), rotation=(1.0, 0.0, 0.0, 0.0)),
    )
    elbow_cuff = Link(
        id="exo_elbow_cuff",
        name="Exo Elbow Cuff",
        transform=Transform(translation=(0.0, -0.15, 0.0), rotation=(1.0, 0.0, 0.0, 0.0)),
    )
    forearm_cuff = Link(
        id="exo_elbow_forearm_cuff",
        name="Exo Elbow Forearm Cuff",
        transform=Transform(translation=(0.0, -0.12, 0.0), rotation=(1.0, 0.0, 0.0, 0.0)),
    )

    # Device sites: elbow pulley for cable wrap, side site for wrap direction.
    elbow_pulley = Site(
        id="exo_elbow_pulley",
        name="Elbow Pulley",
        link_id="exo_elbow_cuff",
        transform=Transform(translation=(0.0, 0.0, 0.03), rotation=(1.0, 0.0, 0.0, 0.0)),
    )
    elbow_pulley_side = Site(
        id="exo_elbow_pulley_side",
        name="Elbow Pulley Side",
        link_id="exo_elbow_cuff",
        transform=Transform(translation=(0.05, 0.0, 0.0), rotation=(1.0, 0.0, 0.0, 0.0)),
    )

    # Cable actuator: runs from upper-arm anchor, wraps around elbow pulley, inserts at radius.
    elbow_cable = Actuator(
        id="elbow_assist_cable",
        name="Elbow Assist Cable",
        kind=ActuatorKind.CABLE,
        route=[
            RouteNode(kind=RouteNodeKind.SITE, site_id=anchor_site_id),
            RouteNode(
                kind=RouteNodeKind.WRAP,
                geometry_id="exo_elbow_pulley",
                side_site_id="exo_elbow_pulley_side",
            ),
            RouteNode(kind=RouteNodeKind.SITE, site_id=insertion_site_id),
        ],
        cable=CableParameters(
            stiffness=1500.0,
            damping=3.0,
            rest_length=0.2,
        ),
    )

    # Motor actuator driving the cable tendon (force-controlled).
    cable_motor = Actuator(
        id="elbow_assist_motor",
        name="Elbow Assist Motor",
        kind=ActuatorKind.MOTOR,
        joint_id=None,
    )

    # Wrap geometry for the elbow pulley (sphere approximating a pulley).
    elbow_wrap_geom = Geometry(
        id="exo_elbow_pulley",
        name="Elbow Pulley Wrap",
        kind="sphere",
        link_id="exo_elbow_cuff",
        site_id="exo_elbow_pulley",
        role=GeometryRole.WRAP,
        parameters={"radius": 0.015},
    )

    # Joints connecting device links into a kinematic chain.
    upper_to_elbow = Joint(
        id="exo_elbow_upper_to_cuff",
        name="Upper Arm to Elbow Cuff",
        kind=JointKind.FIXED,
        parent_link_id="exo_elbow_upper_anchor",
        child_link_id="exo_elbow_cuff",
    )
    elbow_to_forearm = Joint(
        id="exo_elbow_cuff_to_forearm",
        name="Elbow Cuff to Forearm",
        kind=JointKind.FIXED,
        parent_link_id="exo_elbow_cuff",
        child_link_id="exo_elbow_forearm_cuff",
    )

    device = SystemModel(
        id="cable_elbow_exo",
        name="Cable-Driven Elbow Exoskeleton",
        role=SystemRole.DEVICE,
        root_link_id="exo_elbow_upper_anchor",
        links=[upper_arm_anchor, elbow_cuff, forearm_cuff],
        sites=[elbow_pulley, elbow_pulley_side],
        joints=[upper_to_elbow, elbow_to_forearm],
        geometries=[elbow_wrap_geom],
        actuators=[elbow_cable, cable_motor],
    )

    return device


# ---------------------------------------------------------------------------
def build_knee_assembly(anatomical_id: str, device_id: str):
    """Create an assembly connecting the knee exo hip anchor to the pelvis."""
    from melos.core.project.model import AssemblyConnection, AssemblyEndpoint, SystemAssembly

    connection = AssemblyConnection(
        id="knee_exo_to_pelvis",
        name="Knee Exo to Pelvis",
        endpoint_a=AssemblyEndpoint(system_id=anatomical_id, anchor_link_id="sacrum"),
        endpoint_b=AssemblyEndpoint(system_id=device_id, anchor_link_id="exo_hip_anchor"),
    )
    return SystemAssembly(
        id="knee_exo_assembly",
        name="Knee Exoskeleton Assembly",
        connections=[connection],
    )


def build_elbow_assembly(anatomical_id: str, device_id: str):
    """Create an assembly connecting the elbow exo anchor to the humerus."""
    from melos.core.project.model import AssemblyConnection, AssemblyEndpoint, SystemAssembly

    connection = AssemblyConnection(
        id="elbow_exo_to_humerus",
        name="Elbow Exo to Humerus",
        endpoint_a=AssemblyEndpoint(system_id=anatomical_id, anchor_link_id="humerus_r"),
        endpoint_b=AssemblyEndpoint(system_id=device_id, anchor_link_id="exo_elbow_upper_anchor"),
    )
    return SystemAssembly(
        id="elbow_exo_assembly",
        name="Elbow Exoskeleton Assembly",
        connections=[connection],
    )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(*, with_skin: bool = False, output_dir: Path | None = None) -> Project:
    """Execute the full import → device → compile pipeline."""

    if output_dir is None:
        output_dir = _REPO_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Import MyoFullBody ──────────────────────────────────────
    print(f"[1/5] Importing MyoFullBody from {_MYO_FULLBODY_XML} ...")
    result = import_mjcf(_MYO_FULLBODY_XML)
    project = result.project
    anatomical = project.get_anatomical_system()
    assert anatomical is not None
    print(f"       {len(anatomical.links)} links, {len(anatomical.joints)} joints, "
          f"{len(anatomical.actuators)} muscles, {len(anatomical.sites)} sites")

    # ── Step 2 (optional): Fit MHR skin ─────────────────────────────────
    if with_skin:
        print("[2/5] Loading MHR skin bundle and fitting to skeleton ...")
        try:
            from melos.skin.adapters import build_example_mhr_skin_bundle
            skin_bundle = build_example_mhr_skin_bundle(_SKIN_ASSET_DIR)
            if skin_bundle is not None:
                print(f"       Skin mesh: {len(skin_bundle['vertices'])} vertices, "
                      f"{len(skin_bundle['faces'])} faces")
                # Store skin attachment metadata.
                from melos.core.project.assets import AssetRecord
                from melos.core.project.enums import AssetRole
                from melos.core.project.attachment import Attachment, AttachmentFit

                skin_fit = AttachmentFit(
                    anchor_link_id=anatomical.root_link_id or "sacrum",
                    rest_transform_in_anchor=Transform.identity(),
                    reference_link_ids=[link.id for link in anatomical.links[:4]],
                )
                project.attachments.append(
                    Attachment(
                        id="skin_main",
                        name="Human Skin (MHR)",
                        target_system_id=anatomical.id,
                        mesh_asset_id="skin_mesh",
                        binding_asset_id="skin_binding",
                        fit=skin_fit,
                    )
                )
                project.assets.items.append(
                    AssetRecord(id="skin_mesh", name="Skin mesh", role=AssetRole.VISUAL,
                                uri="", media_type="model/obj")
                )
                project.assets.items.append(
                    AssetRecord(id="skin_binding", name="Skin binding", role=AssetRole.FITTING,
                                uri="", media_type="application/vnd.melos.skin-binding+json")
                )
                # Export skin mesh as OBJ for reference.
                _export_skin_obj(skin_bundle, output_dir / "skin_mesh.obj")
                print(f"       Skin mesh exported to {output_dir / 'skin_mesh.obj'}")
            else:
                print("       [WARN] MHR runtime unavailable; skipping skin fitting.")
        except Exception as exc:
            print(f"       [WARN] Skin fitting failed: {exc}; continuing without skin.")
    else:
        print("[2/5] Skipping skin fitting (use --with-skin to enable).")

    # ── Step 3: Add cable exoskeleton devices ───────────────────────────
    print("[3/5] Building cable-driven exoskeleton devices ...")

    knee_device = build_knee_assist_exoskeleton(anatomical)
    project.systems.append(knee_device)
    knee_assembly = build_knee_assembly(anatomical.id, knee_device.id)
    project.assemblies.append(knee_assembly)
    print(f"       Knee device '{knee_device.id}': {len(knee_device.links)} links, "
          f"{len(knee_device.actuators)} actuators (1 cable + 1 motor)")

    elbow_device = build_elbow_assist_exoskeleton(anatomical)
    project.systems.append(elbow_device)
    elbow_assembly = build_elbow_assembly(anatomical.id, elbow_device.id)
    project.assemblies.append(elbow_assembly)
    print(f"       Elbow device '{elbow_device.id}': {len(elbow_device.links)} links, "
          f"{len(elbow_device.actuators)} actuators (1 cable + 1 motor)")

    # ── Step 4: Compile to MJCF ─────────────────────────────────────────
    print("[4/5] Compiling project to MJCF ...")
    compile_result = compile_project(project, validate=False)
    mjcf_path = output_dir / "exoskeleton_model.xml"
    mjcf_path.write_text(compile_result.mjcf_text)
    print(f"       MJCF written to {mjcf_path}")
    if compile_result.report.warnings:
        print(f"       {len(compile_result.report.warnings)} compile warnings:")
        for w in compile_result.report.warnings[:5]:
            print(f"         [{w.code}] {w.message}")
        if len(compile_result.report.warnings) > 5:
            print(f"         ... and {len(compile_result.report.warnings) - 5} more")

    # ── Step 5: Save project JSON ───────────────────────────────────────
    print("[5/5] Saving project JSON ...")
    from melos.core.io.json import save_project
    json_path = output_dir / "exoskeleton_project.json"
    save_project(project, json_path)
    print(f"       Project saved to {json_path}")

    # ── Summary ─────────────────────────────────────────────────────────
    print()
    print("=== Pipeline complete ===")
    print(f"  Anatomical system: {len(anatomical.links)} links, {len(anatomical.actuators)} muscles")
    print(f"  Knee device:       {len(knee_device.links)} links, {len(knee_device.actuators)} actuators")
    print(f"  Elbow device:      {len(elbow_device.links)} links, {len(elbow_device.actuators)} actuators")
    print(f"  Assemblies:        {len(project.assemblies)}")
    print(f"  Attachments:       {len(project.attachments)}")
    print(f"  Output MJCF:       {mjcf_path}")
    print(f"  Output JSON:       {json_path}")
    print()
    print("To visualize in MuJoCo:")
    print(f"  python -m mujoco.viewer --mjcf={mjcf_path}")
    print()
    print("To load in Blender (with the melos addon installed):")
    print("  1. Open Blender → Sidebar → melos tab")
    print(f"  2. Import Project → select {json_path}")
    print("  3. Use 'Create Example Project' for the full skin+fitted workflow")

    return project


def _export_skin_obj(skin_bundle: dict, path: Path) -> None:
    """Export skin mesh vertices/faces as a Wavefront OBJ file."""
    import numpy as np

    vertices = np.asarray(skin_bundle["vertices"])
    faces = np.asarray(skin_bundle["faces"])
    with open(path, "w") as f:
        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for face in faces:
            # OBJ faces are 1-indexed.
            f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--with-skin", action="store_true", help="Enable MHR skin fitting (requires py-soma-x + torch)")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory (default: ./output)")
    args = parser.parse_args()
    run_pipeline(with_skin=args.with_skin, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
