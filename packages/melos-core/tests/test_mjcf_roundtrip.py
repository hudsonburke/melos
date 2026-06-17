"""Roundtrip test: import MyoFullBody, compile, reimport, compile — verify structural equivalence."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


def _normalize_id(id_str: str) -> str:
    """Strip melos compile prefixes (anatomical_link_, anatomical_site_, etc.)."""
    prefixes = [
        "anatomical_link_", "anatomical_site_", "anatomical_wrap_",
        "anatomical_joint_", "anatomical_actuator_",
        "muscle_", "cable_",
        "visual_anatomical_",
    ]
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if id_str.startswith(prefix):
                id_str = id_str[len(prefix):]
                changed = True
                break
    return id_str


def _strip_compiler_prefixes_from_system(system) -> None:
    """Mutate system IDs to strip compiler-added prefixes for comparison."""
    for link in system.links:
        link.id = _normalize_id(link.id)
    for joint in system.joints:
        joint.id = _normalize_id(joint.id)
        joint.parent_link_id = _normalize_id(joint.parent_link_id)
        joint.child_link_id = _normalize_id(joint.child_link_id)
    for site in system.sites:
        site.id = _normalize_id(site.id)
        if site.link_id:
            site.link_id = _normalize_id(site.link_id)
    for actuator in system.actuators:
        actuator.id = _normalize_id(actuator.id)
        if actuator.route:
            for node in actuator.route:
                if node.site_id:
                    node.site_id = _normalize_id(node.site_id)
                if node.geometry_id:
                    node.geometry_id = _normalize_id(node.geometry_id)
                if node.side_site_id:
                    node.side_site_id = _normalize_id(node.side_site_id)
    for geom in system.geometries:
        geom.id = _normalize_id(geom.id)
        if geom.link_id:
            geom.link_id = _normalize_id(geom.link_id)
        if geom.site_id:
            geom.site_id = _normalize_id(geom.site_id)


def test_myofullbody_roundtrip_structural_equivalence() -> None:
    """Import → compile → reimport → compile should preserve model structure."""
    from melos.sim.mujoco.importers import import_mjcf
    from melos.sim import compile_project

    original_path = Path(__file__).parent.parent.parent.parent / (
        "resources/third_party/myofullbody/body/myofullbody.xml"
    )
    if not original_path.exists():
        pytest.skip("MyoFullBody not available")

    # Round 1: import original
    r1 = import_mjcf(str(original_path))
    a1 = r1.project.systems[0]
    c1 = compile_project(r1.project, validate=False)

    # Round 2: compile → reimport → compile
    with tempfile.TemporaryDirectory() as td:
        mjcf_path = Path(td) / "model.xml"
        mjcf_path.write_text(c1.mjcf_text)
        r2 = import_mjcf(str(mjcf_path))
        a2 = r2.project.systems[0]

    # Strip compiler prefixes for fair comparison
    _strip_compiler_prefixes_from_system(a2)

    # ── Count comparison ──
    assert len(a1.links) == len(a2.links), f"links: {len(a1.links)} vs {len(a2.links)}"
    assert len(a1.joints) == len(a2.joints), f"joints: {len(a1.joints)} vs {len(a2.joints)}"
    assert len(a1.sites) == len(a2.sites), f"sites: {len(a1.sites)} vs {len(a2.sites)}"
    assert len(a1.actuators) == len(a2.actuators), f"actuators: {len(a1.actuators)} vs {len(a2.actuators)}"

    # ── Link transform comparison ──
    links1 = {link.id: link for link in a1.links}
    links2 = {link.id: link for link in a2.links}

    missing = set(links1) - set(links2)
    extra = set(links2) - set(links1)
    assert not missing, f"Links missing in round 2: {missing}"
    assert not extra, f"Links extra in round 2: {extra}"

    pos_errors = []
    rot_errors = []
    for lid in sorted(links1):
        t1 = links1[lid].transform
        t2 = links2[lid].transform
        pdiff = sum((a - b) ** 2 for a, b in zip(t1.translation, t2.translation)) ** 0.5
        rdiff = sum((a - b) ** 2 for a, b in zip(t1.rotation, t2.rotation)) ** 0.5
        if pdiff > 0.001:
            pos_errors.append((lid, pdiff))
        if rdiff > 0.001:
            rot_errors.append((lid, rdiff))

    assert not pos_errors, f"Position errors > 1mm ({len(pos_errors)}): {pos_errors[:5]}"
    assert not rot_errors, f"Rotation errors > 0.001 ({len(rot_errors)}): {rot_errors[:5]}"

    # ── Joint comparison ──
    joints1 = {(j.parent_link_id, j.child_link_id): j for j in a1.joints}
    joints2 = {(j.parent_link_id, j.child_link_id): j for j in a2.joints}
    common_joints = set(joints1) & set(joints2)

    for key in sorted(common_joints):
        j1, j2 = joints1[key], joints2[key]
        assert j1.kind == j2.kind, f"Joint kind mismatch for {key}: {j1.kind} vs {j2.kind}"
        if j1.coordinates and j2.coordinates:
            for c1, c2 in zip(j1.coordinates, j2.coordinates):
                adiff = sum((a - b) ** 2 for a, b in zip(c1.axis, c2.axis)) ** 0.5
                assert adiff < 0.001, f"Joint axis mismatch for {key}/{c1.id}: {c1.axis} vs {c2.axis}"

    # ── Site comparison ──
    sites1 = {s.id: s for s in a1.sites}
    sites2 = {s.id: s for s in a2.sites}
    common_sites = set(sites1) & set(sites2)

    for sid in sorted(common_sites):
        s1, s2 = sites1[sid], sites2[sid]
        assert s1.link_id == s2.link_id, f"Site link mismatch for {sid}: {s1.link_id} vs {s2.link_id}"
        pdiff = sum((a - b) ** 2 for a, b in zip(s1.transform.translation, s2.transform.translation)) ** 0.5
        assert pdiff < 0.001, f"Site pos mismatch for {sid}: diff={pdiff:.4f}"

    # ── Actuator route comparison ──
    actuators1 = {a.id: a for a in a1.actuators}
    actuators2 = {a.id: a for a in a2.actuators}
    common_actuators = set(actuators1) & set(actuators2)

    for aid in sorted(common_actuators):
        a1, a2 = actuators1[aid], actuators2[aid]
        assert a1.kind == a2.kind, f"Actuator kind mismatch for {aid}"
        if a1.route and a2.route:
            assert len(a1.route) == len(a2.route), f"Route length mismatch for {aid}"
            for i, (n1, n2) in enumerate(zip(a1.route, a2.route)):
                assert n1.kind == n2.kind, f"Route node {i} kind mismatch for {aid}"
                assert n1.site_id == n2.site_id, f"Route node {i} site mismatch for {aid}"
                assert n1.geometry_id == n2.geometry_id, f"Route node {i} geom mismatch for {aid}"
