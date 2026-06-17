from __future__ import annotations

from melos.blender.bpy_io.importer import import_project_to_scene
from melos.blender.constants import (
    ATTACHMENT_DEVICE_ID_KEY,
    ATTACHMENT_INTERFACE_ID_KEY,
    ATTACHMENT_KIND,
    ATTACHMENT_ANATOMICAL_SITE_ID_KEY,
    DEVICE_ACTUATOR_COORDINATE_ID_KEY,
    DEVICE_ACTUATOR_KIND,
    DEVICE_ACTUATOR_KIND_KEY,
    DEVICE_ACTUATOR_JOINT_ID_KEY,
    DEVICE_FRAME_KIND,
    DEVICE_FRAME_LINK_ID_KEY,
    DEVICE_INTERFACE_KIND,
    DEVICE_INTERFACE_KIND_KEY,
    DEVICE_JOINT_CHILD_LINK_ID_KEY,
    DEVICE_JOINT_KIND,
    DEVICE_JOINT_KIND_KEY,
    DEVICE_JOINT_PARENT_LINK_ID_KEY,
    DEVICE_LINK_ID_KEY,
    DEVICE_LINK_KIND,
    DEVICE_SENSOR_FRAME_ID_KEY,
    DEVICE_SENSOR_KIND,
    DEVICE_SENSOR_KIND_KEY,
    DISPLAY_NAME_KEY,
    ENTITY_ID_KEY,
    ENTITY_KIND_KEY,
    FRAME_LINK_ID_KEY,
    FRAME_IS_ANATOMICAL_KEY,
    JOINT_CHILD_LINK_ID_KEY,
    JOINT_COORDINATE_AXIS_KEY,
    JOINT_COORDINATE_DEFAULT_VALUE_KEY,
    JOINT_COORDINATE_ID_KEY,
    JOINT_COORDINATE_KIND_KEY,
    JOINT_COORDINATE_NAME_KEY,
    JOINT_KIND_KEY,
    JOINT_PARENT_LINK_ID_KEY,
    LANDMARK_BODY_ID_KEY,
    LANDMARK_FRAME_ID_KEY,
    LANDMARK_KIND,
    MUSCLE_ID_KEY,
    MUSCLE_PATH_POINT_LINK_ID_KEY,
    MUSCLE_PATH_POINT_KIND,
    MUSCLE_PATH_POINT_KIND_KEY,
    MUSCLE_PATH_POINT_ORDER_KEY,
    MUSCLE_WRAP_LINK_ID_KEY,
    MUSCLE_WRAP_GEOMETRY_KIND,
    MUSCLE_WRAP_KIND_KEY,
    ANATOMICAL_LINK_KIND,
    ANATOMICAL_SITE_KIND,
    ANATOMICAL_JOINT_KIND,
)
from melos.core.kinematics.model import CoordinateKind, JointKind
from melos.core.kinematics.model import CoordinateDefinition
from melos.core.project.model import ProjectMeta, Project
from melos.core.system import (
    Actuator,
    ActuatorKind,
    AssemblyConnection,
    AssemblyEndpoint,
    ConnectionKind,
    ConstraintPolicy,
    Geometry,
    GeometryRole,
    InterfaceKind,
    Joint,
    Link,
    Sensor,
    SensorKind,
    Site,
    SystemAssembly,
    SystemModel,
    SystemRole,
)


class FakeObject(dict):
    def __init__(self, name: str, *, object_type: str = "EMPTY") -> None:
        super().__init__()
        self.name = name
        self.type = object_type
        self.parent = None
        self.children: list[FakeObject] = []
        self.empty_display_type = ""

    def get(self, key, default=None):
        return super().get(key, default)


class FakeCollection:
    def __init__(self):
        self.linked: list[FakeObject] = []

    def link(self, obj: FakeObject) -> None:
        self.linked.append(obj)


class FakeSettings:
    project_id = ""
    project_name = ""
    anatomical_system_id = ""
    anatomical_system_name = ""
    anatomical_system_root_link_id = ""


class FakeScene:
    def __init__(self):
        self.objects: list[FakeObject] = []
        self.melos_blender = FakeSettings()
        self.collection = FakeCollection()


def fake_create_object(name: str, collection: FakeCollection) -> FakeObject:
    obj = FakeObject(name)
    collection.link(obj)
    return obj


def _make_project() -> Project:
    anatomical = SystemModel(
        id="anatomical",
        name="Anatomical System",
        role=SystemRole.ANATOMICAL,
        root_link_id="pelvis",
        links=[Link(id="pelvis", name="Pelvis"), Link(id="femur", name="Femur")],
        sites=[
            Site(id="pelvis_frame", name="Pelvis Frame", link_id="pelvis", tags=["frame", "anatomical"]),
            Site(id="asis", name="ASIS", link_id="pelvis", parent_site_id="pelvis_frame", tags=["landmark"]),
            Site(id="rf_origin", name="RF Origin", link_id="pelvis", tags=["muscle_path_point", "origin", "rectus_femoris"]),
            Site(id="rf_insert", name="RF Insert", link_id="femur", tags=["muscle_path_point", "insertion", "rectus_femoris"]),
        ],
        joints=[
            Joint(
                id="hip_joint",
                name="Hip Joint",
                kind=JointKind.REVOLUTE,
                parent_link_id="pelvis",
                child_link_id="femur",
                parent_site_id="pelvis_frame",
                coordinates=[
                    CoordinateDefinition(
                        id="hip_flexion",
                        name="Hip Flexion",
                        kind=CoordinateKind.ROTATION,
                        axis=(1.0, 0.0, 0.0),
                        default_value=0.1,
                    )
                ],
            )
        ],
        geometries=[
            Geometry(
                id="patella_wrap",
                name="Patella Wrap",
                kind="cylinder",
                role=GeometryRole.WRAP,
                link_id="pelvis",
                parameters={"radius": 0.02, "height": 0.1},
            )
        ],
        actuators=[
            Actuator(
                id="rectus_femoris",
                name="Rectus Femoris",
                kind=ActuatorKind.MUSCLE,
                site_ids=["rf_origin", "rf_insert"],
                parameters={"wrap_geometry_ids": ["patella_wrap"]},
            )
        ],
    )
    device = SystemModel(
        id="exo",
        name="Exo",
        role=SystemRole.DEVICE,
        root_link_id="thigh",
        links=[Link(id="thigh", name="Thigh")],
        sites=[
            Site(id="cuff_frame", name="Cuff Frame", link_id="thigh", tags=["frame"]),
            Site(
                id="thigh_cuff",
                name="Thigh Cuff",
                link_id="thigh",
                parent_site_id="cuff_frame",
                tags=["interface", "cuff"],
                annotations={"interface_kind": "cuff"},
            ),
        ],
        joints=[
            Joint(
                id="knee_joint",
                name="Knee Joint",
                kind=JointKind.REVOLUTE,
                parent_link_id="thigh",
                child_link_id="thigh",
                coordinates=[
                    CoordinateDefinition(
                        id="knee_flexion",
                        name="Knee Flexion",
                        kind=CoordinateKind.ROTATION,
                        axis=(0.0, 1.0, 0.0),
                    )
                ],
            )
        ],
        sensors=[Sensor(id="imu", name="IMU", kind=SensorKind.IMU, site_id="cuff_frame", link_id="thigh")],
        actuators=[Actuator(id="motor", name="Motor", kind=ActuatorKind.MOTOR, joint_id="knee_joint", coordinate_id="knee_flexion")],
    )
    assembly = SystemAssembly(
        id="assembly",
        connections=[
            AssemblyConnection(
                id="attach_1",
                name="Attach 1",
                endpoint_a=AssemblyEndpoint(
                    system_id="exo",
                    kind=InterfaceKind.CUFF,
                    reference_site_ids=["thigh_cuff"],
                ),
                endpoint_b=AssemblyEndpoint(
                    system_id="anatomical",
                    kind=InterfaceKind.CUSTOM,
                    reference_site_ids=["pelvis_frame"],
                ),
                connection_kind=ConnectionKind.RIGID,
                constraint_policy=ConstraintPolicy.LOWER_TO_WELD,
            )
        ],
    )
    return Project(meta=ProjectMeta(id="proj", name="Test Project"), systems=[anatomical, device], assemblies=[assembly])


def test_import_project_to_scene_creates_anatomical_and_device_objects():
    project = _make_project()
    scene = FakeScene()

    created = import_project_to_scene(project, scene, scene.melos_blender, create_object=fake_create_object)

    assert len(created) >= 10
    kinds = [obj[ENTITY_KIND_KEY] for obj in created]
    assert ANATOMICAL_LINK_KIND in kinds
    assert ANATOMICAL_SITE_KIND in kinds
    assert ANATOMICAL_JOINT_KIND in kinds
    assert LANDMARK_KIND in kinds
    assert MUSCLE_PATH_POINT_KIND in kinds
    assert MUSCLE_WRAP_GEOMETRY_KIND in kinds
    assert DEVICE_LINK_KIND in kinds
    assert DEVICE_FRAME_KIND in kinds
    assert DEVICE_SENSOR_KIND in kinds
    assert DEVICE_ACTUATOR_KIND in kinds
    assert DEVICE_INTERFACE_KIND in kinds
    assert ATTACHMENT_KIND in kinds


def test_import_project_to_scene_maps_core_fields_to_blender_properties():
    project = _make_project()
    scene = FakeScene()

    created = import_project_to_scene(project, scene, scene.melos_blender, create_object=fake_create_object)
    by_id = {obj[ENTITY_ID_KEY]: obj for obj in created if ENTITY_ID_KEY in obj}

    assert by_id["pelvis"][ENTITY_KIND_KEY] == ANATOMICAL_LINK_KIND
    assert by_id["pelvis_frame"][FRAME_LINK_ID_KEY] == "pelvis"
    assert by_id["pelvis_frame"][FRAME_IS_ANATOMICAL_KEY] is True
    assert by_id["hip_joint"][JOINT_PARENT_LINK_ID_KEY] == "pelvis"
    assert by_id["hip_joint"][JOINT_CHILD_LINK_ID_KEY] == "femur"
    assert by_id["hip_joint"][JOINT_KIND_KEY] == "revolute"
    assert by_id["hip_joint"][JOINT_COORDINATE_ID_KEY] == "hip_flexion"
    assert by_id["hip_joint"][JOINT_COORDINATE_NAME_KEY] == "Hip Flexion"
    assert by_id["hip_joint"][JOINT_COORDINATE_KIND_KEY] == "rotation"
    assert by_id["hip_joint"][JOINT_COORDINATE_AXIS_KEY] == (1.0, 0.0, 0.0)
    assert by_id["hip_joint"][JOINT_COORDINATE_DEFAULT_VALUE_KEY] == 0.1
    assert by_id["asis"][LANDMARK_BODY_ID_KEY] == "pelvis"
    assert by_id["asis"][LANDMARK_FRAME_ID_KEY] == "pelvis_frame"
    assert by_id["rf_origin"][MUSCLE_ID_KEY] == "rectus_femoris"
    assert by_id["rf_origin"][MUSCLE_PATH_POINT_KIND_KEY] == "origin"
    assert by_id["rf_origin"][MUSCLE_PATH_POINT_LINK_ID_KEY] == "pelvis"
    assert by_id["rf_origin"][MUSCLE_PATH_POINT_ORDER_KEY] == 0
    assert by_id["patella_wrap"][MUSCLE_WRAP_KIND_KEY] == "cylinder"
    assert by_id["patella_wrap"][MUSCLE_WRAP_LINK_ID_KEY] == "pelvis"
    assert by_id["thigh"][ENTITY_KIND_KEY] == DEVICE_LINK_KIND
    assert by_id["cuff_frame"][DEVICE_FRAME_LINK_ID_KEY] == "thigh"
    assert by_id["knee_joint"][DEVICE_JOINT_KIND_KEY] == "revolute"
    assert by_id["knee_joint"][DEVICE_JOINT_PARENT_LINK_ID_KEY] == "thigh"
    assert by_id["knee_joint"][DEVICE_JOINT_CHILD_LINK_ID_KEY] == "thigh"
    assert by_id["imu"][DEVICE_SENSOR_KIND_KEY] == "imu"
    assert by_id["imu"][DEVICE_SENSOR_FRAME_ID_KEY] == "cuff_frame"
    assert by_id["motor"][DEVICE_ACTUATOR_KIND_KEY] == "motor"
    assert by_id["motor"][DEVICE_ACTUATOR_JOINT_ID_KEY] == "knee_joint"
    assert by_id["motor"][DEVICE_ACTUATOR_COORDINATE_ID_KEY] == "knee_flexion"
    assert by_id["thigh_cuff"][DEVICE_INTERFACE_KIND_KEY] == "cuff"
    assert by_id["attach_1"][ATTACHMENT_DEVICE_ID_KEY] == "exo"
    assert by_id["attach_1"][ATTACHMENT_INTERFACE_ID_KEY] == "thigh_cuff"
    assert by_id["attach_1"][ATTACHMENT_ANATOMICAL_SITE_ID_KEY] == "pelvis_frame"

    assert scene.melos_blender.project_id == "proj"
    assert scene.melos_blender.project_name == "Test Project"
    assert scene.melos_blender.anatomical_system_id == "anatomical"
    assert scene.melos_blender.anatomical_system_name == "Anatomical System"
    assert scene.melos_blender.anatomical_system_root_link_id == "pelvis"
