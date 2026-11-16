"""Rule-based media classification (KBI-105)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MediaClass = str


_DIAGRAM_TOKENS = (
    "diagram",
    "schematic",
    "flowchart",
    "architecture",
    "uml",
    "mermaid",
)


@dataclass(frozen=True)
class ClassifiedMedia:
    filename: str
    data: bytes
    media_type: str
    media_class: MediaClass
    diagram_candidate: bool = False


def classify_image(filename: str, data: bytes, media_type: str, *, primary_asset: bool = False) -> ClassifiedMedia:
    name = Path(filename).name.lower()
    size = len(data)
    if any(token in name for token in ("watermark", "icon", "logo")):
        media_class = "decorative"
    elif any(token in name for token in ("signature", "handwritten", "handwriting")):
        media_class = "handwritten"
    elif any(token in name for token in ("critical", "diagram", "schematic")):
        media_class = "critical"
    elif not primary_asset and size < 512:
        media_class = "decorative"
    elif size > 50_000:
        media_class = "substantive"
    else:
        media_class = "illustrative"
    return ClassifiedMedia(
        filename=filename,
        data=data,
        media_type=media_type,
        media_class=media_class,
        diagram_candidate=is_diagram_candidate(name),
    )


def is_diagram_candidate(filename: str) -> bool:
    name = Path(filename).name.lower()
    return any(token in name for token in _DIAGRAM_TOKENS)


def requires_verification(media_class: str) -> bool:
    return media_class in {"critical", "handwritten"}