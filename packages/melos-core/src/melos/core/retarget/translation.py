from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, kw_only=True)
class SegmentTranslationRule:
    segment_id: str
    source_link_id: str
    target_link_id: str
    source_tail_link_id: str | None = None
    parent_segment_id: str | None = None
    target_joint_ids: list[str] = field(default_factory=list)
    reference_target_joint_ids: list[str] = field(default_factory=list)
    anchor_target_joint_id: str | None = None
    reduction_mode: str = "direct"
    failure_policy: str = "required"
    template_ref_dir: tuple[float, float, float] = (0.0, 0.0, 1.0)
    aliases: list[str] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class TranslationMap:
    id: str
    source_rig: str
    target_rig: str
    version: str
    rules: list[SegmentTranslationRule] = field(default_factory=list)
