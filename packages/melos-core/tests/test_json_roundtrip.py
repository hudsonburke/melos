import json

from melos.core.common.types import Transform
from melos.core.io.json import project_from_json, project_to_json
from melos.core.common.enums import CoordinateKind, JointKind
from melos.core.common.types import CoordinateDefinition
from melos.core.project.model import ProjectMeta, Project
from melos.core.project.skin import SkinAttachment, SkinAttachmentFit
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


def test_project_json_roundtrip() -> None:
    project = Project(
        meta=ProjectMeta(name="demo-project"),
        systems=[
            SystemModel(
                id="human",
                name="Human",
                role=SystemRole.ANATOMICAL,
                root_link_id="pelvis",
                links=[Link(id="pelvis", name="Pelvis")],
                sites=[Site(id="pelvis_site", name="Pelvis Site", link_id="pelvis", tags=["landmark"])],
                joints=[
                    Joint(
                        id="hip",
                        name="Hip",
                        kind=JointKind.REVOLUTE,
                        child_link_id="pelvis",
                        child_site_id="pelvis_site",
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
                        id="pelvis_visual",
                        name="Pelvis Visual",
                        kind="mesh",
                        role=GeometryRole.VISUAL,
                        link_id="pelvis",
                    )
                ],
                actuators=[
                    Actuator(
                        id="hip_flexor",
                        name="Hip Flexor",
                        kind=ActuatorKind.MUSCLE,
                        site_ids=["pelvis_site"],
                    )
                ],
            ),
            SystemModel(
                id="exo_knee",
                name="Knee Exoskeleton",
                role=SystemRole.DEVICE,
                links=[Link(id="thigh_shell", name="Thigh Shell")],
                sites=[Site(id="thigh_cuff_frame", name="Thigh Cuff Frame", link_id="thigh_shell")],
                sensors=[
                    Sensor(
                        id="encoder",
                        name="Encoder",
                        kind=SensorKind.POSITION,
                        site_id="thigh_cuff_frame",
                        measurement_unit="rad",
                    )
                ],
            ),
        ],
        skin_attachments=[
            SkinAttachment(
                id="skin_main",
                name="Main Skin",
                target_system_id="human",
                mesh_asset_id="skin_mesh",
                binding_asset_id="skin_binding",
                fit=SkinAttachmentFit(
                    anchor_link_id="pelvis",
                    rest_transform_in_anchor=Transform.identity(),
                    fit_coordinate_values={"hip_flexion": 0.0},
                    reference_link_ids=["pelvis"],
                    reference_site_ids=["pelvis_site"],
                    reference_geometry_ids=[],
                ),
            )
        ],
        assemblies=[
            SystemAssembly(
                id="human_exo",
                name="Human + Exo",
                connections=[
                    AssemblyConnection(
                        id="attach_thigh",
                        name="Attach Thigh Cuff",
                        endpoint_a=AssemblyEndpoint(
                            system_id="exo_knee",
                            kind=InterfaceKind.CUFF,
                            reference_site_ids=["thigh_cuff_frame"],
                        ),
                        endpoint_b=AssemblyEndpoint(
                            system_id="human",
                            kind=InterfaceKind.SOFT_TISSUE_REGION,
                            reference_site_ids=["pelvis_site"],
                        ),
                        connection_kind=ConnectionKind.RIGID,
                        constraint_policy=ConstraintPolicy.LOWER_TO_WELD,
                    )
                ],
                couplings=[
                    CoordinateCoupling(
                        id="knee_coupling",
                        name="Knee Coupling",
                        source_coordinate_id="human_knee_flex",
                        target_coordinate_id="exo_knee_flex",
                    )
                ],
            )
        ],
    )

    payload = project_to_json(project)
    restored = project_from_json(payload)

    assert restored.meta.name == "demo-project"
    assert restored.systems[0].role == SystemRole.ANATOMICAL
    assert restored.systems[0].joints[0].kind == JointKind.REVOLUTE
    assert restored.systems[0].joints[0].coordinates[0].kind == CoordinateKind.ROTATION
    assert restored.skin_attachments[0].target_system_id == "human"
    assert restored.skin_attachments[0].fit.anchor_link_id == "pelvis"
    assert restored.skin_attachments[0].fit.reference_geometry_ids == []
    assert restored.assemblies[0].connections[0].connection_kind == ConnectionKind.RIGID
    assert restored.assemblies[0].connections[0].constraint_policy == ConstraintPolicy.LOWER_TO_WELD


def test_project_from_json_structures_tuple_typed_fields() -> None:
    payload = json.dumps(
        {
            "schema_version": "0.1.0",
            "meta": {"id": "tuple_project", "name": "Tuple Project"},
            "systems": [
                {
                    "id": "human",
                    "name": "Human",
                    "role": "anatomical",
                    "root_link_id": "pelvis",
                    "links": [
                        {
                            "id": "pelvis",
                            "name": "Pelvis",
                            "transform": {
                                "translation": [1.0, 2.0, 3.0],
                                "rotation": [1.0, 0.0, 0.0, 0.0],
                            },
                            "inertial": {
                                "mass": 10.0,
                                "center_of_mass": [0.0, 0.0, 0.0],
                                "inertia_about_com": [0.1, 0.2, 0.3, 0.0, 0.0, 0.0],
                            },
                        }
                    ],
                    "sites": [
                        {
                            "id": "pelvis_site",
                            "name": "Pelvis Site",
                            "link_id": "pelvis",
                            "transform": {
                                "translation": [4.0, 5.0, 6.0],
                                "rotation": [1.0, 0.0, 0.0, 0.0],
                            },
                            "tags": ["landmark"],
                        }
                    ],
                    "joints": [],
                    "geometries": [],
                    "actuators": [],
                    "sensors": [],
                }
            ],
            "assemblies": [],
            "assets": {"items": []},
            "control": {"observations": [], "commands": []},
            "simulation": {
                "compile_target": "mujoco",
                "gravity": [0.0, 0.0, -9.81],
                "time_step": 0.001,
                "duration": None,
                "visual_asset_roles": ["visual"],
                "collision_asset_roles": ["collision", "simulation"],
                "initial_coordinate_values": {},
            },
        }
    )

    restored = project_from_json(payload)

    assert restored.simulation.gravity == (0.0, 0.0, -9.81)
    assert restored.systems[0].links[0].transform.translation == (1.0, 2.0, 3.0)
    assert restored.systems[0].sites[0].transform.translation == (4.0, 5.0, 6.0)
    assert restored.systems[0].links[0].inertial is not None
    assert restored.systems[0].links[0].inertial.center_of_mass == (0.0, 0.0, 0.0)
    assert restored.systems[0].links[0].inertial.inertia_about_com == (0.1, 0.2, 0.3, 0.0, 0.0, 0.0)


def test_project_from_json_rejects_wrong_fixed_tuple_length() -> None:
    payload = json.dumps(
        {
            "schema_version": "0.1.0",
            "meta": {"id": "bad_tuple_project", "name": "Bad Tuple Project"},
            "systems": [
                {
                    "id": "human",
                    "name": "Human",
                    "role": "anatomical",
                    "links": [
                        {
                            "id": "pelvis",
                            "name": "Pelvis",
                            "inertial": {
                                "mass": 10.0,
                                "center_of_mass": [0.0, 0.0, 0.0],
                                "inertia_about_com": [0.1, 0.2, 0.3],
                            },
                        }
                    ],
                    "sites": [],
                    "joints": [],
                    "geometries": [],
                    "actuators": [],
                    "sensors": [],
                }
            ],
            "assemblies": [],
            "assets": {"items": []},
            "control": {"observations": [], "commands": []},
            "simulation": {
                "compile_target": "mujoco",
                "gravity": [0.0, 0.0, -9.81],
                "time_step": 0.001,
                "duration": None,
                "visual_asset_roles": ["visual"],
                "collision_asset_roles": ["collision", "simulation"],
                "initial_coordinate_values": {},
            },
        }
    )

    try:
        project_from_json(payload)
    except ValueError as exc:
        assert "Expected tuple of length 6" in str(exc)
    else:
        raise AssertionError("Expected project_from_json to reject malformed inertia_about_com")
