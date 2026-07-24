"""SOMA-X mesh deformer driven by MuJoCo joint angles.

Uses SOMALayer's forward pass to deform the MHR mesh based on MuJoCo
coordinate values, bypassing the Blender armature for skin deformation.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class SOMADeformer:
    """Deforms an MHR mesh using SOMA-X, driven by MuJoCo joint angles.

    Usage::

        deformer = SOMADeformer(data_root, identity_coeffs, scale_params)
        posed_vertices = deformer.pose(mujoco_coord_values)
    """

    def __init__(
        self,
        data_root: str,
        identity_coeffs: list[float] | None = None,
        scale_params: list[float] | None = None,
    ) -> None:
        import importlib

        self._torch = importlib.import_module("torch")
        self._layer = None
        self._data_root = data_root
        self._identity_coeffs = identity_coeffs or []
        self._scale_params = scale_params or []
        self._rest_vertices: np.ndarray | None = None
        self._prepared = False

    def _ensure_layer(self) -> Any:
        if self._layer is not None:
            return self._layer

        from soma import SOMALayer

        self._layer = SOMALayer(
            data_root=self._data_root,
            identity_model_type="mhr",
            device="cpu",
            mode="dense",
            enable_procedural_transforms=False,
        )

        # Prepare identity
        num_identity = int(getattr(self._layer.identity_model, "num_identity_coeffs", 45))
        num_scale = int(getattr(self._layer.identity_model, "num_scale_params", 68))

        torch = self._torch
        id_list = list(map(float, self._identity_coeffs)) if self._identity_coeffs else [0.0] * num_identity
        sc_list = list(map(float, self._scale_params)) if self._scale_params else [0.0] * num_scale

        identity_tensor = torch.tensor([id_list], dtype=torch.float32)
        scale_tensor = torch.tensor([sc_list], dtype=torch.float32)

        self._layer.prepare_identity(identity_tensor, scale_tensor)
        self._prepared = True

        return self._layer

    def get_rest_vertices(self) -> np.ndarray:
        """Get the rest-pose vertices in meters (B=1, V, 3) → (V, 3)."""
        if self._rest_vertices is not None:
            return self._rest_vertices

        layer = self._ensure_layer()
        torch = self._torch

        # Zero pose = rest pose
        poses = torch.zeros(1, 77, 3, dtype=torch.float32)
        output = layer.pose(poses=poses, transl=torch.zeros(1, 3), apply_correctives=False)
        self._rest_vertices = output.vertices[0].detach().cpu().numpy()
        return self._rest_vertices

    def pose(
        self,
        somax_rotations: np.ndarray,
        root_translation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> np.ndarray:
        """Apply SOMA-X pose and return deformed vertices.

        Parameters
        ----------
        somax_rotations :
            (77, 3) axis-angle rotations for SOMA-X joints.
        root_translation :
            Root (Hips) translation in meters.

        Returns
        -------
        np.ndarray
            (V, 3) posed vertex positions in meters.
        """
        layer = self._ensure_layer()
        torch = self._torch

        # Convert to tensor
        rot_tensor = torch.tensor(somax_rotations, dtype=torch.float32).unsqueeze(0)  # (1, 77, 3)
        transl_tensor = torch.tensor([root_translation], dtype=torch.float32)  # (1, 3)

        output = layer.pose(
            poses=rot_tensor,
            transl=transl_tensor,
            pose2rot=True,
            absolute_pose=True,
            apply_correctives=False,
        )

        return output.vertices[0].detach().cpu().numpy()

    def pose_from_mujoco_angles(
        self,
        mujoco_coord_values: dict[str, float],
        mapping: dict[str, Any] | None = None,
    ) -> np.ndarray:
        """Convenience: convert MuJoCo angles to SOMA-X rotations, then pose.

        Parameters
        ----------
        mujoco_coord_values :
            {coordinate_id: angle_in_radians} from MuJoCo FK.
        mapping :
            Pre-computed mapping from ``build_mujoco_to_soma_mapping()``.
            If None, uses identity (no rotation mapping).

        Returns
        -------
        np.ndarray
            (V, 3) posed vertex positions in meters.
        """
        from .mujoco_to_soma import convert_mujoco_angles_to_soma_rotations

        if mapping is None:
            from .mujoco_to_soma import build_mujoco_to_soma_mapping
            from melos.sim import import_mjcf
            from pathlib import Path

            project = import_mjcf(
                str(Path(self._data_root).parent.parent / "myofullbody" / "body" / "myofullbody.xml")
            ).project
            anatomical = project.get_anatomical_system()
            from melos.skin.mappings.myofullbody_to_human_v1 import build_myofullbody_translation_map
            mapping = build_mujoco_to_soma_mapping(anatomical, build_myofullbody_translation_map())

        rotations = convert_mujoco_angles_to_soma_rotations(mujoco_coord_values, mapping)
        return self.pose(rotations)
