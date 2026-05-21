from melos.core.common.types import Bounds, Transform
from melos.core.kinematics.enums import CoordinateKind, JointKind
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
    InterfaceKind,
    Joint,
    Link,
    Site,
    SystemAssembly,
    SystemModel,
    SystemRole,
)
from melos.core.validation import validate_project


def test_validate_project_accepts_minimal_shared_system_project() -> None:
    project = Project(
        systems=[
            SystemModel(
                id="human",
                name="Human",
                role=SystemRole.ANATOMICAL,
                root_link_id="pelvis",
                links=[Link(id="pelvis", name="Pelvis")],
                sites=[Site(id="pelvis_site", name="Pelvis Site", link_id="pelvis")],
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
            ),
            SystemModel(
                id="exo",
                name="Exo",
                role=SystemRole.DEVICE,
                root_link_id="base",
                links=[Link(id="base", name="Base")],
                sites=[Site(id="cuff_frame", name="Cuff Frame", link_id="base")],
                actuators=[
                    Actuator(
                        id="knee_motor",
                        name="Knee Motor",
                        kind=ActuatorKind.MOTOR,
                        command_limits=Bounds(lower=-1.0, upper=1.0),
                    )
                ],
            ),
        ],
        assemblies=[
            SystemAssembly(
                id="assembly",
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
                            system_id="human",
                            kind=InterfaceKind.SOFT_TISSUE_REGION,
                            reference_site_ids=["pelvis_site"],
                        ),
                        connection_kind=ConnectionKind.COMPLIANT,
                        constraint_policy=ConstraintPolicy.LOWER_TO_SPRINGS,
                    )
                ],
                couplings=[
                    CoordinateCoupling(
                        id="hip_coupling",
                        name="Hip Coupling",
                        source_coordinate_id="hip_flexion",
                        target_coordinate_id="hip_flexion",
                    )
                ],
            )
        ],
    )

    report = validate_project(project)

    assert report.issues == []


def test_validate_project_reports_missing_references() -> None:
    project = Project(
        systems=[
            SystemModel(
                id="exo",
                name="Exo",
                role=SystemRole.DEVICE,
                root_link_id="missing_root",
                links=[Link(id="base", name="Base")],
                sites=[Site(id="cuff_frame", name="Cuff Frame", link_id="missing_link")],
                actuators=[
                    Actuator(
                        id="knee_motor",
                        name="Knee Motor",
                        kind=ActuatorKind.MOTOR,
                        joint_id="missing_joint",
                        coordinate_id="missing_coordinate",
                        site_ids=["missing_site"],
                    )
                ],
            )
        ],
        assemblies=[
            SystemAssembly(
                id="assembly",
                connections=[
                    AssemblyConnection(
                        id="binding",
                        name="Binding",
                        endpoint_a=AssemblyEndpoint(
                            system_id="exo",
                            kind=InterfaceKind.CUFF,
                            reference_site_ids=["missing_site"],
                        ),
                        endpoint_b=AssemblyEndpoint(
                            system_id="human",
                            kind=InterfaceKind.SOFT_TISSUE_REGION,
                            reference_site_ids=["missing_region"],
                        ),
                    )
                ],
            )
        ],
    )

    report = validate_project(project)
    locations = {issue.location for issue in report.issues}

    assert "systems[exo].root_link_id" in locations
    assert "systems[exo].sites[cuff_frame].link_id" in locations
    assert "systems[exo].actuators[knee_motor].joint_id" in locations
    assert "systems[exo].actuators[knee_motor].coordinate_id" in locations
    assert "systems[exo].actuators[knee_motor].site_ids" in locations
    assert "assemblies[assembly].connections[binding].endpoint_a.reference_site_ids" in locations
    assert "assemblies[assembly].connections[binding].endpoint_b.system_id" in locations


def test_validate_project_reports_duplicate_ids_and_invalid_bounds() -> None:
    project = Project(
        systems=[
            SystemModel(
                id="human",
                name="Human",
                role=SystemRole.ANATOMICAL,
                links=[Link(id="pelvis", name="Pelvis"), Link(id="pelvis", name="Pelvis Duplicate")],
                sites=[Site(id="pelvis_site", name="Pelvis Site", link_id="pelvis")],
                actuators=[
                    Actuator(
                        id="motor",
                        name="Motor",
                        kind=ActuatorKind.MOTOR,
                        command_limits=Bounds(lower=2.0, upper=1.0),
                    )
                ],
            )
        ],
        assemblies=[
            SystemAssembly(
                id="assembly",
                connections=[
                    AssemblyConnection(
                        id="binding",
                        name="Binding",
                        endpoint_a=AssemblyEndpoint(system_id="human", kind=InterfaceKind.CUSTOM),
                        relative_transform=Transform(rotation=(0.0, 0.0, 0.0, 0.0)),
                    )
                ],
            )
        ],
    )

    report = validate_project(project)
    codes = {issue.code for issue in report.issues}
    locations = {issue.location for issue in report.issues}

    assert "topology.duplicate_id" in codes
    assert "bounds.invalid" in codes
    assert "transform.zero_quaternion" in codes
    assert "systems[human].links" in locations
    assert "systems[human].actuators[motor].command_limits" in locations
    assert "assemblies[assembly].connections[binding].relative_transform" in locations
