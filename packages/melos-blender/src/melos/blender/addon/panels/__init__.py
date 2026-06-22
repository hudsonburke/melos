"""Panel definitions for the melos Blender add-on."""

from .project import CLASSES as PROJECT_CLASSES
from .subject import CLASSES as SUBJECT_CLASSES
from .device import CLASSES as DEVICE_CLASSES

CLASSES = PROJECT_CLASSES + SUBJECT_CLASSES + DEVICE_CLASSES

__all__ = ["CLASSES"]
