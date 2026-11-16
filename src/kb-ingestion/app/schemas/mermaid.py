"""Mermaid evidence-gate models (KBI.5.4)."""

from __future__ import annotations

from pydantic import BaseModel


class MermaidActivateRequest(BaseModel):
    human_spot_check: bool = False
    license_ok: bool = False


class MermaidRouteReport(BaseModel):
    enabled: bool
    reasons: list[str]
