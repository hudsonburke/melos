"""Operator definitions for the melos Blender add-on."""

from .assembly import CLASSES as ASSEMBLY_CLASSES
from .device import CLASSES as DEVICE_CLASSES
from .importer import CLASSES as IMPORTER_CLASSES
from .landmark import CLASSES as LANDMARK_CLASSES
from .muscle import CLASSES as MUSCLE_CLASSES
from .project import CLASSES as PROJECT_CLASSES
from .anatomical import CLASSES as ANATOMICAL_CLASSES
from .joints import CLASSES as JOINTS_CLASSES

CLASSES = PROJECT_CLASSES + ANATOMICAL_CLASSES + DEVICE_CLASSES + ASSEMBLY_CLASSES + MUSCLE_CLASSES + LANDMARK_CLASSES + IMPORTER_CLASSES + JOINTS_CLASSES

__all__ = ["CLASSES"]
