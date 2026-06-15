"""Cable-routing authoring + round-trip tests for the Blender bridge (fake bpy)."""

from __future__ import annotations

from melos.blender.bpy_io.device import build_device_from_scene
from melos.blender.bpy_io.importer import import_project_to_scene
from melos.core.project.model import Project
from melos.core.system import (
    Actuator,
    ActuatorKind,
    RouteNode,
    RouteNodeKind,
    SystemModel,
    SystemRole,
)


class FakeObject(dict):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.parent = None
        self.children: list[FakeObject] = []
        self.empty_display_type = ""

    def get(self, key, default=None):
        return super().get(key, default)


class FakeCollection:
    def __init__(self) -> None:
        self.linked: list[FakeObject] = []

    def link(self, obj: FakeObject) -> None:
        self.linked.append(obj)


class FakeDeviceSettings:
    def __init__(self, *, device_id: str = "device") -> None:
        self.device_id = device_id
        self.device_name = device_id
        self.device_root_link_id = ""
        self.project_id = ""
        self.project_name = ""
        self.anatomical_system_id = ""
        self.anatomical_system_name = ""
        self.anatomical_system_root_link_id = ""


class FakeScene:
    def __init__(self, objects: list[FakeObject], settings: FakeDeviceSettings | None = None) -> None:
        self.objects = objects
        self.melos_blender = settings or FakeDeviceSettings()
        self.collection = FakeCollection()


def fake_create_object(name: str, collection: FakeCollection) -> FakeObject:
    obj = FakeObject(name)
    collection.link(obj)
    return obj


def _route_point(
    name: str,
    *,
    actuator_id: str,
    order: float,
    node_kind: str,
    site_id: str = "",
    geometry_id: str = "",
    side_site_id: str = "",
) -> FakeObject:
    obj = FakeObject(name)
    obj["melos_entity_kind"] = "device_cable_route_point"
    obj["melos_id"] = name
    obj["melos_cable_actuator_id"] = actuator_id
    obj["melos_cable_route_order"] = order
    obj["melos_cable_route_node_kind"] = node_kind
    obj["melos_cable_route_site_id"] = site_id
    obj["melos_cable_route_geometry_id"] = geometry_id
    obj["melos_cable_route_side_site_id"] = side_site_id
    return obj


def test_build_device_from_scene_attaches_ordered_cable_route() -> None:
    actuator = FakeObject("drive")
    actuator["melos_entity_kind"] = "device_actuator"
    actuator["melos_id"] = "drive"
    actuator["melos_name"] = "Drive"
    actuator["melos_device_actuator_kind"] = "cable"

    # Deliberately out of order to verify route points sort by order.
    point_2 = _route_point("p2", actuator_id="drive", order=2.0, node_kind="site", site_id="insertion")
    point_0 = _route_point("p0", actuator_id="drive", order=0.0, node_kind="site", site_id="anchor")
    point_1 = _route_point(
        "p1",
        actuator_id="drive",
        order=1.0,
        node_kind="wrap",
        geometry_id="pulley",
        side_site_id="pulley_side",
    )

    system = build_device_from_scene(FakeScene([actuator, point_2, point_0, point_1]), FakeDeviceSettings())

    cable = system.actuators[0]
    assert cable.kind == ActuatorKind.CABLE
    assert [node.kind for node in cable.route] == [
        RouteNodeKind.SITE,
        RouteNodeKind.WRAP,
        RouteNodeKind.SITE,
    ]
    assert cable.route[0].site_id == "anchor"
    assert cable.route[1].geometry_id == "pulley"
    assert cable.route[1].side_site_id == "pulley_side"
    assert cable.route[2].site_id == "insertion"


def test_cable_route_round_trips_through_importer() -> None:
    device = SystemModel(
        id="exo",
        name="Exo",
        role=SystemRole.DEVICE,
        actuators=[
            Actuator(
                id="drive",
                name="Drive",
                kind=ActuatorKind.CABLE,
                route=[
                    RouteNode(kind=RouteNodeKind.SITE, site_id="anchor"),
                    RouteNode(kind=RouteNodeKind.WRAP, geometry_id="pulley", side_site_id="pulley_side"),
                    RouteNode(kind=RouteNodeKind.SITE, site_id="insertion"),
                ],
            )
        ],
    )
    project = Project(systems=[device])

    scene = FakeScene([])
    created = import_project_to_scene(
        project,
        scene,
        scene.melos_blender,
        create_object=fake_create_object,
    )

    rebuilt = build_device_from_scene(FakeScene(created, FakeDeviceSettings(device_id="exo")), FakeDeviceSettings(device_id="exo"))

    cable = next(actuator for actuator in rebuilt.actuators if actuator.id == "drive")
    assert cable.kind == ActuatorKind.CABLE
    assert [node.kind for node in cable.route] == [
        RouteNodeKind.SITE,
        RouteNodeKind.WRAP,
        RouteNodeKind.SITE,
    ]
    assert cable.route[0].site_id == "anchor"
    assert cable.route[1].geometry_id == "pulley"
    assert cable.route[1].side_site_id == "pulley_side"
    assert cable.route[2].site_id == "insertion"
