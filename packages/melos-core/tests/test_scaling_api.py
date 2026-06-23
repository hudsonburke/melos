from __future__ import annotations

import pytest

from melos.core.common.types import Transform
from melos.core.common.enums import JointKind
from melos.core.project.model import Project
from melos.core.retarget.model import SegmentMeasurement, SegmentMeasurementSet
from melos.core.scaling import (
    compute_segment_scale_factors_from_measurements,
    fit_project_system_to_measurements,
)
from melos.core.common.enums import GeometryRole, SystemRole
from melos.core.system.model import Geometry, Joint, Link, Site, SystemModel


def test_compute_segment_scale_factors_from_measurements_converts_units() -> None:
    source_measurements = SegmentMeasurementSet(
        items=[
            SegmentMeasurement(segment_id="thigh", length=0.5),
            SegmentMeasurement(segment_id="shank", length=0.4),
        ],
        units="m",
    )
    target_measurements = SegmentMeasurementSet(
        items=[
            SegmentMeasurement(segment_id="thigh", length=60.0),
            SegmentMeasurement(segment_id="shank", length=44.0),
        ],
        units="cm",
    )

    scale_factors = compute_segment_scale_factors_from_measurements(
        source_measurements,
        target_measurements,
    )

    assert scale_factors["thigh"] == pytest.approx(1.2)
    assert scale_factors["shank"] == pytest.approx(1.1)


def test_fit_project_system_to_measurements_scales_selected_links_and_dependents() -> None:
    system = SystemModel(
        id="anatomical",
        name="Anatomical System",
        role=SystemRole.ANATOMICAL,
        root_link_id="pelvis",
        links=[
            Link(id="pelvis", name="Pelvis"),
            Link(id="femur", name="Femur", transform=Transform(translation=(0.0, 0.0, -0.5))),
            Link(id="tibia", name="Tibia", transform=Transform(translation=(0.0, 0.0, -0.4))),
        ],
        joints=[
            Joint(
                id="hip",
                name="Hip",
                kind=JointKind.FIXED,
                parent_link_id="pelvis",
                child_link_id="femur",
            ),
            Joint(
                id="knee",
                name="Knee",
                kind=JointKind.FIXED,
                parent_link_id="femur",
                child_link_id="tibia",
            ),
        ],
        sites=[
            Site(
                id="tibia_site",
                name="Tibia Site",
                link_id="tibia",
                transform=Transform(translation=(0.0, 0.0, -0.1)),
            )
        ],
        geometries=[
            Geometry(
                id="tibia_geom",
                name="Tibia Geometry",
                kind="capsule",
                role=GeometryRole.CUSTOM,
                link_id="tibia",
                transform=Transform(translation=(0.0, 0.0, -0.2)),
                parameters={"radius": 0.05, "length": 0.3},
            )
        ],
    )
    project = Project(systems=[system])

    source_measurements = SegmentMeasurementSet(
        items=[
            SegmentMeasurement(segment_id="thigh", length=0.5),
            SegmentMeasurement(segment_id="shank", length=0.4),
        ],
        units="m",
    )
    target_measurements = SegmentMeasurementSet(
        items=[
            SegmentMeasurement(segment_id="thigh", length=60.0),
            SegmentMeasurement(segment_id="shank", length=44.0),
        ],
        units="cm",
    )

    fit_result = fit_project_system_to_measurements(
        project,
        source_measurements,
        target_measurements,
        {
            "thigh": ("femur",),
            "shank": ("tibia",),
        },
    )

    scaled_system = fit_result.project.get_anatomical_system()
    assert scaled_system is not None
    links_by_id = {link.id: link for link in scaled_system.links}
    sites_by_id = {site.id: site for site in scaled_system.sites}
    geometries_by_id = {geometry.id: geometry for geometry in scaled_system.geometries}

    assert fit_result.segment_scale_factors["thigh"] == pytest.approx(1.2)
    assert fit_result.segment_scale_factors["shank"] == pytest.approx(1.1)
    assert fit_result.link_scale_factors["femur"] == pytest.approx(1.2)
    assert fit_result.link_scale_factors["tibia"] == pytest.approx(1.1)

    assert links_by_id["femur"].transform.translation == pytest.approx((0.0, 0.0, -0.6))
    assert links_by_id["tibia"].transform.translation == pytest.approx((0.0, 0.0, -0.44))
    assert sites_by_id["tibia_site"].transform.translation == pytest.approx((0.0, 0.0, -0.11))
    assert geometries_by_id["tibia_geom"].transform.translation == pytest.approx((0.0, 0.0, -0.22))
    assert geometries_by_id["tibia_geom"].parameters["radius"] == pytest.approx(0.055)
    assert geometries_by_id["tibia_geom"].parameters["length"] == pytest.approx(0.33)

    original_system = project.get_anatomical_system()
    assert original_system is not None
    original_links = {link.id: link for link in original_system.links}
    assert original_links["femur"].transform.translation == (0.0, 0.0, -0.5)
    assert original_links["tibia"].transform.translation == (0.0, 0.0, -0.4)
