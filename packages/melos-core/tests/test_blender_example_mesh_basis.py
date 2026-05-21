from __future__ import annotations

import pytest

from melos.blender.addon.operators.project import _align_generic_humanoid


def test_align_generic_humanoid_converts_obj_y_up_into_template_z_up() -> None:
    vertices = [
        [-1.0, -2.0, -0.1],
        [1.0, 2.0, 0.2],
        [0.0, 0.0, 0.0],
    ]
    identity = {
        "rotation": (
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        ),
        "scale": 1.0,
        "translation": (0.0, 0.0, 0.0),
    }

    aligned = _align_generic_humanoid(vertices, identity)

    # Height should now live on +Z, while preserving the OBJ origin.
    assert aligned[0] == pytest.approx([-1.0, -0.1, -2.0])
    assert aligned[1] == pytest.approx([1.0, 0.2, 2.0])
    assert aligned[2] == pytest.approx([0.0, 0.0, 0.0])
