"""Asset selection helpers for MuJoCo compilation."""

from __future__ import annotations

from melos.core.project.model import Project

from ..reports import AssetBinding


def build_asset_manifest(project: Project) -> list[AssetBinding]:
    """Select project assets relevant to the current simulation preferences."""

    visual_roles = set(project.simulation.visual_asset_roles)
    collision_roles = set(project.simulation.collision_asset_roles)
    manifest: list[AssetBinding] = []

    for asset in project.assets.items:
        if asset.role in visual_roles:
            manifest.append(
                AssetBinding(
                    asset_id=asset.id,
                    role=asset.role,
                    uri=asset.uri,
                    usage="visual",
                )
            )
        if asset.role in collision_roles:
            manifest.append(
                AssetBinding(
                    asset_id=asset.id,
                    role=asset.role,
                    uri=asset.uri,
                    usage="collision",
                )
            )

    return manifest
