from melos.core.common.types import Bounds, InertialProperties, Transform
from melos.core.kinematics.model import CoordinateKind, JointKind
from melos.core.kinematics.model import CoordinateDefinition
from melos.core.project.model import Project
from melos.core.system import (
    Actuator,
    ActuatorKind,
    AssemblyConnection,
    AssemblyEndpoint,
    ConnectionKind,
    ConstraintPolicy,
    CoordinateCoupling,
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


def test_system_model_supports_shared_anatomical_like_structure():
    system = SystemModel(
        id="human",
        name="Human",
        role=SystemRole.ANATOMICAL,
        root_link_id="pelvis",
        links=[
            Link(
                id="pelvis",
                name="Pelvis",
                transform=Transform(translation=(0.0, 0.0, 1.0)),
                inertial=InertialProperties(
                    mass=10.0,
                    center_of_mass=(0.0, 0.0, 0.0),
                    inertia_about_com=(1.0, 1.0, 1.0, 0.0, 0.0, 0.0),
                ),
                asset_ids=["pelvis_mesh"],
            ),
            Link(id="femur_r", name="Femur R"),
        ],
        sites=[
            Site(id="hip_r", name="Hip R", link_id="pelvis", tags=["frame", "anatomical"]),
            Site(
                id="asis_r",
                name="ASIS R",
                link_id="pelvis",
                parent_site_id="hip_r",
                transform=Transform(translation=(0.1, 0.2, 0.3)),
                tags=["landmark", "right"],
            ),
        ],
        joints=[
            Joint(
                id="hip_joint_r",
                name="Hip Joint R",
                kind=JointKind.REVOLUTE,
                parent_link_id="pelvis",
                child_link_id="femur_r",
                parent_site_id="hip_r",
                coordinates=[
                    CoordinateDefinition(
                        id="hip_flex_r",
                        name="Hip Flex R",
                        kind=CoordinateKind.ROTATION,
                        axis=(1.0, 0.0, 0.0),
                    )
                ],
            )
        ],
        geometries=[
            Geometry(
                id="hip_wrap",
                name="Hip Wrap",
                kind="cylinder",
                role=GeometryRole.WRAP,
                link_id="pelvis",
                parameters={"radius": 0.02, "height": 0.1},
            ),
            Geometry(
                id="pelvis_contact",
                name="Pelvis Contact",
                kind="box",
                role=GeometryRole.CONTACT,
                link_id="pelvis",
                parameters={"size": (0.1, 0.2, 0.3)},
            ),
        ],
        actuators=[
            Actuator(
                id="glute_max_r",
                name="Glute Max R",
                kind=ActuatorKind.MUSCLE,
                link_ids=["pelvis", "femur_r"],
                site_ids=["hip_r", "asis_r"],
                parameters={"max_isometric_force": 1200.0},
            )
        ],
    )

    assert system.role is SystemRole.ANATOMICAL
    assert system.links[0].asset_ids == ["pelvis_mesh"]
    assert system.sites[1].tags == ["landmark", "right"]
    assert system.joints[0].coordinates[0].kind is CoordinateKind.ROTATION
    assert system.geometries[0].role is GeometryRole.WRAP
    assert system.actuators[0].kind is ActuatorKind.MUSCLE


def test_project_uses_systems_and_assemblies_as_top_level_structure():
    anatomical = SystemModel(id="human", name="Human", role=SystemRole.ANATOMICAL)
    device = SystemModel(
        id="exo",
        name="Exo",
        role=SystemRole.DEVICE,
        links=[Link(id="base", name="Base")],
        sites=[Site(id="thigh_cuff_frame", name="Thigh Cuff Frame", link_id="base")],
        sensors=[
            Sensor(
                id="knee_encoder",
                name="Knee Encoder",
                kind=SensorKind.POSITION,
                site_id="thigh_cuff_frame",
                measurement_unit="rad",
            )
        ],
        actuators=[
            Actuator(
                id="knee_motor",
                name="Knee Motor",
                kind=ActuatorKind.MOTOR,
                command_limits=Bounds(lower=-1.0, upper=1.0),
            )
        ],
    )
    assembly = SystemAssembly(
        id="human_exo",
        name="Human + Exo",
        connections=[
            AssemblyConnection(
                id="left_thigh_binding",
                name="Left Thigh Binding",
                endpoint_a=AssemblyEndpoint(
                    system_id="exo",
                    kind=InterfaceKind.CUFF,
                    reference_site_ids=["thigh_cuff_frame"],
                ),
                endpoint_b=AssemblyEndpoint(
                    system_id="human",
                    kind=InterfaceKind.SOFT_TISSUE_REGION,
                    reference_site_ids=["left_thigh_region"],
                ),
                connection_kind=ConnectionKind.COMPLIANT,
                constraint_policy=ConstraintPolicy.LOWER_TO_SPRINGS,
            )
        ],
        couplings=[
            CoordinateCoupling(
                id="couple_knee",
                name="Couple Knee",
                source_coordinate_id="human_knee_flex",
                target_coordinate_id="exo_knee_flex",
                scale=1.0,
                offset=0.0,
            )
        ],
    )
    project = Project(systems=[anatomical, device], assemblies=[assembly])

    assert project.get_system("human") is anatomical
    assert project.get_system("exo") is device
    assert project.get_system("missing") is None
    assert project.get_primary_system_by_role("anatomical") is anatomical
    assert project.get_anatomical_system() is anatomical
    assert project.assemblies[0].connections[0].connection_kind is ConnectionKind.COMPLIANT
    assert project.assemblies[0].connections[0].constraint_policy is ConstraintPolicy.LOWER_TO_SPRINGS
    assert project.assemblies[0].couplings[0].target_coordinate_id == "exo_knee_flex"
