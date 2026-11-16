"""Rule-based media classification (KBI-105)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MediaClass = str


@dataclass(frozen=True)
class ClassifiedMedia:
    filename: str
    data: bytes
    media_type: str
    media_class: MediaClass


def classify_image(filename: str, data: bytes, media_type: str) -> ClassifiedMedia:
    name = Path(filename).name.lower()
    size = len(data)
    if size < 512 or any(token in name for token in ("watermark", "icon", "logo")):
        media_class = "decorative"
    elif any(token in name for token in ("signature", "handwritten", "handwriting")):
        media_class = "handwritten"
    elif any(token in name for token in ("critical", "diagram", "schematic")):
        media_class = "critical"
    elif size > 50_000:
        media_class = "substantive"
    else:
        media_class = "illustrative"
    return ClassifiedMedia(
        filename=filename,
        data=data,
        media_type=media_type,
        media_class=media_class,
    )


def requires_verification(media_class: str) -> bool:
    return media_class in {"critical", "handwritten"}