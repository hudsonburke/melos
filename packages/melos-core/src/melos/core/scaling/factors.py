from __future__ import annotations

from collections import deque

from melos.core.common.transforms import vec3_length
from melos.core.common.types import Vec3
from melos.core.scaling.skeleton import SegmentNode

JointCorrespondenceMap = dict[str, str]
ScaleFactorMap = dict[str, float]


def compute_scale_factors(
    skeleton: dict[str, SegmentNode],
    link_vectors: dict[str, Vec3],
    joint_map: JointCorrespondenceMap,
) -> ScaleFactorMap:
    reversed_map: dict[str, str] = {v: k for k, v in joint_map.items()}

    roots = [n for n in skeleton.values() if n.parent_id is None]

    result: ScaleFactorMap = {}

    queue: deque[SegmentNode] = deque(roots)
    while queue:
        node = queue.popleft()
        link_id = node.link_id

        if node.parent_id is None:
            result[link_id] = 1.0
        elif link_id in reversed_map:
            joint_name = reversed_map[link_id]
            if joint_name not in link_vectors:
                raise ValueError(
                    f"Anatomical joint '{joint_name}' not found in link_vectors"
                )
            link_length = vec3_length(link_vectors[joint_name])
            ref_length = vec3_length(node.position)
            if ref_length < 1e-12:
                result[link_id] = 1.0
            else:
                result[link_id] = link_length / ref_length
        else:
            result[link_id] = result.get(node.parent_id, 1.0)

        for child in node.children:
            queue.append(child)

    return result
