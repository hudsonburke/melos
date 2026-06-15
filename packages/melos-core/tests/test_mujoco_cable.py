"""MJCF lowering tests for routed cable and muscle actuators."""

from __future__ import annotations

from xml.etree.ElementTree import fromstring

from melos.core.common.types import Bounds
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
from melos.sim import compile_project


def _device_with_cable(*, cable: CableParameters | None = None, command_limits: Bounds | None = None) -> Project:
    route = [
        RouteNode(kind=RouteNodeKind.SITE, site_id="anchor"),
        RouteNode(kind=RouteNodeKind.WRAP, geometry_id="pulley", side_site_id="pulley_side"),
        RouteNode(kind=RouteNodeKind.SITE, site_id="insertion"),
    ]
    device = SystemModel(
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
                id="drive",
                name="Drive",
                kind=ActuatorKind.CABLE,
                route=route,
                cable=cable,
                command_limits=command_limits,
            )
        ],
    )
    return Project(systems=[device])


def test_cable_actuator_lowers_to_tendon_and_motor() -> None:
    cable = CableParameters(stiffness=120.0, damping=2.0, width=0.002)
    result = compile_project(_device_with_cable(cable=cable), validate=True)
    root = fromstring(result.mjcf_text)

    spatial = root.find("./tendon/spatial[@name='cable_drive']")
    assert spatial is not None
    assert spatial.get("stiffness") == "120"
    assert spatial.get("damping") == "2"
    assert spatial.get("width") == "0.002"

    # Ordered path: site -> wrap geom (with sidesite) -> site
    children = list(spatial)
    assert [child.tag for child in children] == ["site", "geom", "site"]
    assert children[0].get("site") == "exo_site_anchor"
    assert children[1].get("geom") == "exo_wrap_pulley"
    assert children[1].get("sidesite") == "exo_site_pulley_side"
    assert children[2].get("site") == "exo_site_insertion"

    motor = root.find("./actuator/motor[@name='exo_actuator_drive']")
    assert motor is not None
    assert motor.get("tendon") == "cable_drive"


def test_cable_command_limits_become_ctrlrange() -> None:
    result = compile_project(
        _device_with_cable(command_limits=Bounds(lower=-50.0, upper=50.0)),
        validate=True,
    )
    root = fromstring(result.mjcf_text)

    motor = root.find("./actuator/motor[@name='exo_actuator_drive']")
    assert motor is not None
    assert motor.get("ctrlrange") == "-50 50"


def test_cable_route_length_range_limits_tendon() -> None:
    cable = CableParameters(length_range=Bounds(lower=0.1, upper=0.5))
    result = compile_project(_device_with_cable(cable=cable), validate=True)
    root = fromstring(result.mjcf_text)

    spatial = root.find("./tendon/spatial[@name='cable_drive']")
    assert spatial is not None
    assert spatial.get("range") == "0.1 0.5"
    assert spatial.get("limited") == "true"


def test_routed_muscle_emits_driving_actuator_and_wraps_geom() -> None:
    muscle = SystemModel(
        id="body",
        name="Body",
        role=SystemRole.ANATOMICAL,
        root_link_id="pelvis",
        links=[Link(id="pelvis", name="Pelvis")],
        sites=[
            Site(id="origin", name="Origin", link_id="pelvis"),
            Site(id="insertion", name="Insertion", link_id="pelvis"),
        ],
        geometries=[
            Geometry(
                id="wrap",
                name="Wrap",
                kind="sphere",
                role=GeometryRole.WRAP,
                link_id="pelvis",
                parameters={"radius": 0.02},
            )
        ],
        actuators=[
            Actuator(
                id="biceps",
                name="Biceps",
                kind=ActuatorKind.MUSCLE,
                route=[
                    RouteNode(kind=RouteNodeKind.SITE, site_id="origin"),
                    RouteNode(kind=RouteNodeKind.WRAP, geometry_id="wrap"),
                    RouteNode(kind=RouteNodeKind.SITE, site_id="insertion"),
                ],
                parameters={"physiology": {"max_isometric_force": 500.0}},
            )
        ],
    )
    result = compile_project(Project(systems=[muscle]), validate=True)
    root = fromstring(result.mjcf_text)

    spatial = root.find("./tendon/spatial[@name='muscle_biceps']")
    assert spatial is not None
    assert [child.tag for child in spatial] == ["site", "geom", "site"]
    assert spatial.find("geom").get("geom") == "body_wrap_wrap"

    muscle_actuator = root.find("./actuator/muscle[@name='body_muscle_biceps']")
    assert muscle_actuator is not None
    assert muscle_actuator.get("tendon") == "muscle_biceps"
    assert muscle_actuator.get("force") == "500"

    # A routed muscle wires the wrap geom directly, so no approximation warning fires.
    assert all(w.code != "muscle.wrap.approximation" for w in result.report.warnings)
