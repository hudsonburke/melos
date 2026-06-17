import json
from importlib import import_module
from pathlib import Path

from melos.core.assets.model import AssetLibrary, AssetRecord
from melos.core.common.types import AssetRole, Transform
from melos.core.control.model import CommandChannel, ControlInterface, ObservationChannel
from melos.core.kinematics.model import CoordinateKind, JointKind
from melos.core.kinematics.model import CoordinateDefinition
from melos.core.project.model import ProjectMeta, Project
from melos.core.simulation.model import SimulationConfig
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
from melos.sim import compile_project, compile_project_file


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def _build_project() -> Project:
    anatomical = SystemModel(
        id="anatomical",
        name="Anatomical System",
        role=SystemRole.ANATOMICAL,
        root_link_id="pelvis",
        links=[Link(id="pelvis", name="Pelvis", asset_ids=["pelvis_mesh"]), Link(id="femur", name="Femur")],
        sites=[
            Site(id="hip_site", name="Hip Site", link_id="pelvis"),
            Site(id="knee_site", name="Knee Site", link_id="femur"),
            Site(id="left_thigh_region", name="Left Thigh Region", link_id="pelvis"),
        ],
        joints=[
            Joint(
                id="hip_joint",
                name="Hip Joint",
                kind=JointKind.REVOLUTE,
                parent_link_id="pelvis",
                child_link_id="femur",
                coordinates=[
                    CoordinateDefinition(
                        id="hip_flexion",
                        name="Hip Flexion",
                        kind=CoordinateKind.ROTATION,
                        axis=(1.0, 0.0, 0.0),
                    )
                ],
            )
        ],
        geometries=[
            Geometry(
                id="patella_wrap",
                name="Patella Wrap",
                kind="sphere",
                role=GeometryRole.WRAP,
                link_id="pelvis",
                parameters={"radius": 0.03},
            ),
            Geometry(
                id="foot_contact",
                name="Foot Contact",
                kind="sphere",
                role=GeometryRole.CONTACT,
                link_id="pelvis",
                parameters={"size": (0.05,)},
            ),
        ],
        actuators=[
            Actuator(
                id="rectus_femoris",
                name="Rectus Femoris",
                kind=ActuatorKind.MUSCLE,
                site_ids=["hip_site", "knee_site"],
                parameters={"wrap_geometry_ids": ["patella_wrap"]},
            )
        ],
    )
    device = SystemModel(
        id="exo",
        name="Exo",
        role=SystemRole.DEVICE,
        root_link_id="base",
        links=[Link(id="base", name="Base"), Link(id="shank", name="Shank")],
        sites=[Site(id="cuff_frame", name="Cuff Frame", link_id="base")],
        joints=[
            Joint(
                id="exo_knee_joint",
                name="Exo Knee Joint",
                kind=JointKind.REVOLUTE,
                parent_link_id="base",
                child_link_id="shank",
                coordinates=[
                    CoordinateDefinition(
                        id="exo_knee_flexion",
                        name="Exo Knee Flexion",
                        kind=CoordinateKind.ROTATION,
                        axis=(0.0, 1.0, 0.0),
                    )
                ],
            )
        ],
        actuators=[
            Actuator(
                id="knee_motor",
                name="Knee Motor",
                kind=ActuatorKind.MOTOR,
                joint_id="exo_knee_joint",
            )
        ],
        sensors=[
            Sensor(
                id="knee_encoder",
                name="Knee Encoder",
                kind=SensorKind.POSITION,
                link_id="shank",
            )
        ],
    )
    assembly = SystemAssembly(
        id="human_exo",
        name="Human + Exo",
        connections=[
            AssemblyConnection(
                id="left_binding",
                name="Left Binding",
                endpoint_a=AssemblyEndpoint(
                    system_id="exo",
                    kind=InterfaceKind.CUFF,
                    reference_site_ids=["cuff_frame"],
                ),
                endpoint_b=AssemblyEndpoint(
                    system_id="anatomical",
                    kind=InterfaceKind.SOFT_TISSUE_REGION,
                    reference_site_ids=["left_thigh_region"],
                ),
                relative_transform=Transform.identity(),
                connection_kind=ConnectionKind.COMPLIANT,
                constraint_policy=ConstraintPolicy.LOWER_TO_SPRINGS,
            )
        ],
        couplings=[
            CoordinateCoupling(
                id="hip_to_exo",
                name="Hip To Exo",
                source_coordinate_id="hip_flexion",
                target_coordinate_id="exo_knee_flexion",
            )
        ],
    )
    return Project(
        meta=ProjectMeta(id="demo_project", name="Demo Project"),
        assets=AssetLibrary(items=[AssetRecord(id="pelvis_mesh", name="Pelvis Mesh", uri="pelvis.obj", role=AssetRole.VISUAL)]),
        systems=[anatomical, device],
        assemblies=[assembly],
        simulation=SimulationConfig(),
        control=ControlInterface(
            observations=[ObservationChannel(id="hip_obs", name="Hip Obs", source_ref="/systems/anatomical/joints/hip_joint/coordinates/hip_flexion")],
            commands=[CommandChannel(id="exo_cmd", name="Exo Cmd", target_ref="/systems/exo/actuators/knee_motor")],
        ),
    )


def test_mujoco_namespace_import() -> None:
    module = import_module("melos.sim.mujoco")
    assert module.__version__ == "0.1.0"


def test_shared_system_project_compiles_to_mjcf() -> None:
    project = _build_project()

    result = compile_project(project, validate=False)

    assert '<mujoco model="demo_project">' in result.mjcf_text
    assert 'body name="anatomical_link_pelvis"' in result.mjcf_text
    assert 'body name="exo_link_base"' in result.mjcf_text
    assert 'geom name="anatomical_wrap_patella_wrap"' in result.mjcf_text
    assert 'geom name="contact_foot_contact"' in result.mjcf_text
    assert 'spatial name="muscle_rectus_femoris"' in result.mjcf_text
    assert 'motor name="exo_actuator_knee_motor"' in result.mjcf_text
    assert 'jointpos name="exo_sensor_knee_encoder"' in result.mjcf_text
    assert result.signal_map.observations[0].backend_name == "observation_hip_obs"
    assert result.signal_map.commands[0].backend_name == "exo_actuator_knee_motor"
    assert [warning.code for warning in result.report.warnings] == ["muscle.wrap.approximation"]


def test_compile_project_file_reads_shared_system_schema(tmp_path: Path) -> None:
    project = _build_project()
    project_path = tmp_path / "project.json"
    project_path.write_text(json.dumps(project.to_dict()))

    result = compile_project_file(project_path, validate=False)

    assert 'body name="anatomical_link_pelvis"' in result.mjcf_text
