from importlib import import_module

from melos.core.common.units import ACCELERATION_UNIT
from melos.core.project.model import Project
from melos.core.simulation.model import SimulationConfig
from melos.core.system import Actuator, ActuatorKind, SystemModel, SystemRole
from melos.core.validation import validate_project


def test_namespace_import() -> None:
    module = import_module("melos.core")
    assert module.__version__ == "0.1.0"


def test_project_defaults() -> None:
    project = Project()
    assert project.schema_version == "0.1.0"
    assert project.systems == []
    assert project.assemblies == []


def test_system_actuator_import() -> None:
    actuator = Actuator(id="gastroc_med", name="Gastrocnemius Medialis", kind=ActuatorKind.MUSCLE)
    system = SystemModel(id="human", name="Human", role=SystemRole.ANATOMICAL, actuators=[actuator])
    assert system.actuators[0].id == "gastroc_med"


def test_validation_runs_on_defaults() -> None:
    report = validate_project(Project())
    assert report.issues == []


def test_acceleration_unit_name_is_spelled_correctly() -> None:
    assert ACCELERATION_UNIT == "m/s^2"
    assert SimulationConfig.__dataclass_fields__["gravity"].metadata["unit"] == ACCELERATION_UNIT
