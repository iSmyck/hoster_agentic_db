"""Evidence-gated diagram→Mermaid route (KBI.5)."""

from __future__ import annotations

from ..adapters.kroki_client import KrokiClient, StubKrokiClient
from ..adapters.vision_llm import StubVisionLLM, VisionLLM, VisionLLMError
from ..schemas.mermaid import MermaidRouteReport


class MermaidConversion:
    def __init__(
        self,
        *,
        source: str | None,
        status: str,
        error: str | None = None,
    ) -> None:
        self.source = source
        self.status = status
        self.error = error


class MermaidRoute:
    def __init__(
        self,
        vision: VisionLLM | None = None,
        kroki: KrokiClient | None = None,
    ) -> None:
        self.vision = vision or StubVisionLLM()
        self.kroki = kroki or StubKrokiClient()
        self.human_spot_check = False
        self.license_ok = False
        self._golden_cached = False

    @property
    def enabled(self) -> bool:
        return not self.status().reasons

    def status(self) -> MermaidRouteReport:
        reasons: list[str] = []
        if not self.vision.configured:
            reasons.append("VISION_PROVIDER_MISSING")
        if not self.kroki.available:
            reasons.append("KROKI_UNAVAILABLE")
        if not self.human_spot_check:
            reasons.append("HUMAN_SPOT_CHECK_REQUIRED")
        if not self.license_ok:
            reasons.append("LICENSE_CHECK_FAILED")
        if not self._golden_cached:
            reasons.append("GOLDEN_FIXTURES_FAILED")
        return MermaidRouteReport(enabled=not reasons, reasons=reasons)

    def activate(self, *, human_spot_check: bool, license_ok: bool) -> MermaidRouteReport:
        self.human_spot_check = human_spot_check
        self.license_ok = license_ok
        self._golden_cached = self.vision.golden_pass()
        return self.status()

    def convert_diagram(self, filename: str, data: bytes) -> MermaidConversion:
        if not self.enabled:
            return MermaidConversion(source=None, status="skipped")
        try:
            source = self.vision.generate_mermaid(filename, data)
        except VisionLLMError as exc:
            return MermaidConversion(source=None, status="skipped", error=exc.message)
        if not self.kroki.validate_mermaid(source):
            return MermaidConversion(
                source=None,
                status="invalid",
                error="MERMAID_INVALID",
            )
        return MermaidConversion(source=source, status="validated")
