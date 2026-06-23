"""Tests for cable/tendon routing primitives on the shared actuator model."""

from melos.core.system.model import Bounds
from melos.core.io.json import project_from_json, project_to_json
from melos.core.project.model import Project
from melos.core.system import (
    Actuator,
    ActuatorKind,
    CableParameters,
    Geometry,
    GeometryRole,
    Link,
    RouteNode,
    RouteNodeKind,
    Site,
    SystemModel,
    SystemRole,
)
from melos.core.validation import validate_project


def _device_system(*, route: list[RouteNode], cable: CableParameters | None = None) -> SystemModel:
    return SystemModel(
        id="exo",
        name="Exo",
        role=SystemRole.DEVICE,
        root_link_id="base",
        links=[Link(id="base", name="Base")],
        sites=[
            Site(id="anchor", name="Anchor", link_id="base"),
            Site(id="insertion", name="Insertion", link_id="base"),
            Site(id="pulley_side", name="Pulley Side", link_id="base"),
        ],
        geometries=[
            Geometry(
                id="pulley",
                name="Pulley",
                kind="cylinder",
                role=GeometryRole.WRAP,
                link_id="base",
                parameters={"radius": 0.01, "height": 0.04},
            )
        ],
        actuators=[
            Actuator(
                id="cable",
                name="Cable",
                kind=ActuatorKind.CABLE,
                route=route,
                cable=cable,
            )
        ],
    )


def test_valid_cable_route_passes_validation() -> None:
    route = [
        RouteNode(kind=RouteNodeKind.SITE, site_id="anchor"),
        RouteNode(kind=RouteNodeKind.WRAP, geometry_id="pulley", side_site_id="pulley_side"),
        RouteNode(kind=RouteNodeKind.SITE, site_id="insertion"),
    ]
    project = Project(systems=[_device_system(route=route, cable=CableParameters(stiffness=120.0))])

    report = validate_project(project)

    assert report.issues == []


def test_cable_route_reports_missing_references() -> None:
    route = [
        RouteNode(kind=RouteNodeKind.SITE, site_id="missing_site"),
        RouteNode(kind=RouteNodeKind.WRAP, geometry_id="missing_wrap", side_site_id="missing_side"),
        RouteNode(kind=RouteNodeKind.SITE, site_id="insertion"),
    ]
    project = Project(systems=[_device_system(route=route)])

    report = validate_project(project)
    locations = {issue.location for issue in report.issues}

    assert "systems[exo].actuators[cable].route[0].site_id" in locations
    assert "systems[exo].actuators[cable].route[1].geometry_id" in locations
    assert "systems[exo].actuators[cable].route[1].side_site_id" in locations


def test_under_specified_cable_is_warning_not_error() -> None:
    route = [RouteNode(kind=RouteNodeKind.SITE, site_id="anchor")]
    project = Project(systems=[_device_system(route=route)])

    report = validate_project(project)

    assert not report.has_errors
    cable_warnings = [issue for issue in report.issues if issue.code == "topology.cable_route_too_short"]
    assert len(cable_warnings) == 1
    assert cable_warnings[0].location == "systems[exo].actuators[cable].route"


def test_cable_route_survives_json_round_trip() -> None:
    route = [
        RouteNode(kind=RouteNodeKind.SITE, site_id="anchor"),
        RouteNode(kind=RouteNodeKind.WRAP, geometry_id="pulley", side_site_id="pulley_side"),
        RouteNode(kind=RouteNodeKind.SITE, site_id="insertion"),
    ]
    cable = CableParameters(
        rest_length=0.3,
        stiffness=120.0,
        damping=2.0,
        pre_tension=5.0,
        width=0.002,
        length_range=Bounds(lower=0.1, upper=0.5),
    )
    project = Project(systems=[_device_system(route=route, cable=cable)])

    restored = project_from_json(project_to_json(project))

    actuator = restored.systems[0].actuators[0]
    assert [node.kind for node in actuator.route] == [
        RouteNodeKind.SITE,
        RouteNodeKind.WRAP,
        RouteNodeKind.SITE,
    ]
    assert actuator.route[1].geometry_id == "pulley"
    assert actuator.route[1].side_site_id == "pulley_side"
    assert actuator.cable is not None
    assert actuator.cable.stiffness == 120.0
    assert actuator.cable.length_range == Bounds(lower=0.1, upper=0.5)
