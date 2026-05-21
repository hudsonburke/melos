from __future__ import annotations

from dataclasses import dataclass, field

from melos.core.common.types import Vec3
from melos.core.system.model import SystemModel


@dataclass(slots=True, kw_only=True)
class SegmentNode:
    link_id: str
    parent_id: str | None
    position: Vec3
    children: list["SegmentNode"] = field(default_factory=list)


def extract_skeleton_tree(system: SystemModel) -> dict[str, SegmentNode]:
    link_map = {link.id: link for link in system.links}

    parent_of: dict[str, str] = {}
    for joint in system.joints:
        if joint.child_link_id and joint.parent_link_id:
            parent_of[joint.child_link_id] = joint.parent_link_id

    root_id = system.root_link_id

    nodes: dict[str, SegmentNode] = {}
    for link_id, link in link_map.items():
        parent_id = None if link_id == root_id else parent_of.get(link_id)
        nodes[link_id] = SegmentNode(
            link_id=link_id,
            parent_id=parent_id,
            position=link.transform.translation,
        )

    for node in nodes.values():
        if node.parent_id is not None and node.parent_id in nodes:
            nodes[node.parent_id].children.append(node)

    return nodes
