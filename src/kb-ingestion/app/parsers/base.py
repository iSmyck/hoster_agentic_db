"""Shared parser types and errors."""

from __future__ import annotations

from dataclasses import dataclass, field


class ParserError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ExtractedMedia:
    filename: str
    data: bytes
    media_type: str


@dataclass
class ParseResult:
    markdown_body: str
    embedded_media: list[ExtractedMedia] = field(default_factory=list)
    losses: list[dict[str, str]] = field(default_factory=list)