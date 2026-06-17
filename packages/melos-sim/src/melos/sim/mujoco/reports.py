"""Compile result models for ``melos.sim.mujoco``."""

from __future__ import annotations

from dataclasses import dataclass, field

from melos.core.common.types import AssetRole


@dataclass(slots=True, kw_only=True)
class CompileWarning:
    """Single non-fatal warning emitted during MuJoCo compilation."""

    code: str
    message: str
    location: str


@dataclass(slots=True, kw_only=True)
class CompileReport:
    """Aggregate report for a MuJoCo compile pass."""

    warnings: list[CompileWarning] = field(default_factory=list)

    def add_warning(self, *, code: str, message: str, location: str) -> None:
        """Append a warning to the report."""

        self.warnings.append(
            CompileWarning(code=code, message=message, location=location)
        )


@dataclass(slots=True, kw_only=True)
class AssetBinding:
    """Single asset selected for MuJoCo-facing compilation outputs."""

    asset_id: str
    role: AssetRole
    uri: str
    usage: str


@dataclass(slots=True, kw_only=True)
class SignalBinding:
    """Stable control signal mapped onto a backend-specific object."""

    signal_id: str
    external_name: str
    reference: str
    backend_type: str
    backend_name: str


@dataclass(slots=True, kw_only=True)
class SignalMap:
    """Backend signal bindings exported by the compiler."""

    observations: list[SignalBinding] = field(default_factory=list)
    commands: list[SignalBinding] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class MujocoCompileResult:
    """Primary output of the minimal MuJoCo compiler."""

    mjcf_text: str
    asset_manifest: list[AssetBinding] = field(default_factory=list)
    signal_map: SignalMap = field(default_factory=SignalMap)
    report: CompileReport = field(default_factory=CompileReport)
