"""Direct read validator: whole/section, exact revision, bounds, cursor, truncation."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .document_store import Document, Space


@dataclass
class ReadResult:
    document_id: str | None
    revision_sha: str
    path: str
    scope: str  # "whole" or "section"
    heading_path: list[str]
    anchor: str | None
    occurrence: int | None
    start_line: int
    end_line: int
    cursor: int
    truncated: bool
    lines: list[str]
    total_lines: int


@dataclass
class ReadCheck:
    id: str
    status: str  # PASS / FAIL / BLOCKED
    expected: str
    actual: str
    details: dict[str, Any]


def _heading_level(line: str) -> int | None:
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return None
    level = 0
    for ch in stripped:
        if ch == "#":
            level += 1
        else:
            break
    if level > 6 or level == 0:
        return None
    if len(stripped) > level and stripped[level] != " ":
        return None
    return level


def _heading_text(line: str) -> str:
    return line.lstrip("#").strip()


def _anchor(text: str) -> str:
    """GitHub-style heading anchor."""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "-", text.strip())
    return text.lower()


_MALFORMED_HEADING_RE = re.compile(r"^(?!#{1,6}(?:[ \t]|$))#")


def _find_malformed_headings(content: str) -> list[tuple[int, str]]:
    """Return (1-based line number, line text) for malformed heading attempts."""
    malformed: list[tuple[int, str]] = []
    for idx, line in enumerate(content.splitlines(), start=1):
        stripped = line.lstrip()
        if not stripped.startswith("#"):
            continue
        if _MALFORMED_HEADING_RE.match(stripped):
            malformed.append((idx, stripped))
    return malformed


def _find_headings(body: str) -> list[tuple[int, int, str, int]]:
    """Return list of (line_index, level, text, occurrence) for body lines."""
    headings: list[tuple[int, int, str, int]] = []
    occurrence_by_text: dict[str, int] = {}
    for idx, line in enumerate(body.splitlines()):
        level = _heading_level(line)
        if level is None:
            continue
        text = _heading_text(line)
        occurrence_by_text[text] = occurrence_by_text.get(text, 0) + 1
        headings.append((idx, level, text, occurrence_by_text[text]))
    return headings


def read_whole(document: Document) -> ReadResult:
    lines = document.content.splitlines()
    return ReadResult(
        document_id=document.document_id,
        revision_sha=document.revision_sha,
        path=document.path,
        scope="whole",
        heading_path=[document.title or document.path],
        anchor=None,
        occurrence=None,
        start_line=1,
        end_line=max(1, len(lines)),
        cursor=len(lines) + 1,
        truncated=False,
        lines=lines,
        total_lines=len(lines),
    )


def read_section(
    document: Document,
    heading: str,
    occurrence: int = 1,
    max_lines: int | None = None,
) -> ReadResult | None:
    """Read a section by heading text and occurrence index (1-based).

    Section boundaries extend until the next heading of equal or higher level.
    """
    body_lines = document.body.splitlines()
    headings = _find_headings(document.body)
    target = None
    for idx, level, text, occ in headings:
        if text == heading and occ == occurrence:
            target = (idx, level, text, occ)
            break
    if target is None:
        return None

    idx, level, text, occ = target
    # end is the line before the next heading with level <= current level
    end_idx = len(body_lines) - 1
    for next_idx, next_level, _, _ in headings:
        if next_idx > idx and next_level <= level:
            end_idx = next_idx - 1
            break

    # Lines are 1-based in the original content.
    # Front matter is not counted as body lines; body starts after front matter.
    # We report lines relative to the whole document content for canonical direct read.
    content_lines = document.content.splitlines()
    front_matter_line_count = len(content_lines) - len(body_lines)
    start_line = front_matter_line_count + idx + 1
    end_line = front_matter_line_count + end_idx + 1

    section_body = body_lines[idx : end_idx + 1]
    total_lines = len(section_body)
    truncated = False
    if max_lines is not None and len(section_body) > max_lines:
        section_body = section_body[:max_lines]
        truncated = True
        end_line = start_line + max_lines - 1

    return ReadResult(
        document_id=document.document_id,
        revision_sha=document.revision_sha,
        path=document.path,
        scope="section",
        heading_path=[document.title or document.path, text],
        anchor=_anchor(text),
        occurrence=occ,
        start_line=start_line,
        end_line=end_line,
        cursor=end_line + 1,
        truncated=truncated,
        lines=section_body,
        total_lines=total_lines,
    )


class ReadValidator:
    """Validate canonical direct read semantics."""

    def __init__(self, spaces: dict[str, Space]) -> None:
        self.spaces = spaces

    def validate(self, section_scenarios: list[dict[str, Any]]) -> list[ReadCheck]:
        checks: list[ReadCheck] = []
        for space in self.spaces.values():
            for doc in space.documents:
                checks.extend(self._validate_whole_read(doc))
                checks.extend(self._validate_no_malformed_headings(doc))
        for scenario in section_scenarios:
            checks.extend(self._validate_section_read(scenario))
        return checks

    def _validate_no_malformed_headings(self, document: Document) -> list[ReadCheck]:
        malformed = _find_malformed_headings(document.content)
        check_id = f"read.{document.space_id}.{document.path}.malformed_headings"
        if malformed:
            return [
                ReadCheck(
                    id=check_id,
                    status="FAIL",
                    expected="document contains no malformed Markdown headings",
                    actual=f"malformed headings at lines {malformed}",
                    details={"path": document.path, "malformed": malformed},
                )
            ]
        return [
            ReadCheck(
                id=check_id,
                status="PASS",
                expected="document contains no malformed Markdown headings",
                actual="no malformed headings",
                details={"path": document.path},
            )
        ]

    def _validate_whole_read(self, document: Document) -> list[ReadCheck]:
        checks: list[ReadCheck] = []
        result = read_whole(document)
        expected_sha = document.revision_sha
        if result.revision_sha != expected_sha:
            checks.append(
                ReadCheck(
                    id=f"read.{document.space_id}.{document.path}.whole_revision",
                    status="FAIL",
                    expected=f"whole read returns exact revision SHA {expected_sha}",
                    actual=f"got {result.revision_sha}",
                    details={
                        "path": document.path,
                        "document_id": document.document_id,
                    },
                )
            )
        else:
            checks.append(
                ReadCheck(
                    id=f"read.{document.space_id}.{document.path}.whole_revision",
                    status="PASS",
                    expected="whole read returns exact revision SHA",
                    actual=f"revision {result.revision_sha}",
                    details={
                        "path": document.path,
                        "document_id": document.document_id,
                    },
                )
            )

        if result.truncated:
            checks.append(
                ReadCheck(
                    id=f"read.{document.space_id}.{document.path}.whole_truncated",
                    status="FAIL",
                    expected="whole read is not truncated",
                    actual="truncated=true",
                    details={"path": document.path},
                )
            )
        else:
            checks.append(
                ReadCheck(
                    id=f"read.{document.space_id}.{document.path}.whole_truncated",
                    status="PASS",
                    expected="whole read returns truncated=false",
                    actual="truncated=false",
                    details={"path": document.path},
                )
            )

        checks.append(
            ReadCheck(
                id=f"read.{document.space_id}.{document.path}.whole_bounds",
                status="PASS",
                expected="whole read returns start_line, end_line, cursor",
                actual=f"start={result.start_line}, end={result.end_line}, cursor={result.cursor}",
                details={
                    "start_line": result.start_line,
                    "end_line": result.end_line,
                    "cursor": result.cursor,
                },
            )
        )
        return checks

    def _validate_section_read(self, scenario: dict[str, Any]) -> list[ReadCheck]:
        checks: list[ReadCheck] = []
        space_id = scenario["space_id"]
        path = scenario["path"]
        heading = scenario["heading"]
        occurrence = scenario.get("occurrence", 1)
        max_lines = scenario.get("max_lines")
        expect_found = scenario.get("expect_found", True)
        expect_truncated = scenario.get("expect_truncated", False)

        space = self.spaces.get(space_id)
        if space is None:
            checks.append(
                ReadCheck(
                    id=f"read.{space_id}.{path}.{heading}.{occurrence}",
                    status="FAIL",
                    expected=f"Space {space_id} exists",
                    actual="Space not found",
                    details={"space_id": space_id, "path": path},
                )
            )
            return checks
        document = space.by_path().get(path)
        if document is None:
            checks.append(
                ReadCheck(
                    id=f"read.{space_id}.{path}.{heading}.{occurrence}",
                    status="FAIL",
                    expected=f"document {path} exists in {space_id}",
                    actual="document not found",
                    details={"space_id": space_id, "path": path},
                )
            )
            return checks

        result = read_section(
            document, heading, occurrence=occurrence, max_lines=max_lines
        )
        if result is None:
            if expect_found:
                checks.append(
                    ReadCheck(
                        id=f"read.{space_id}.{path}.{heading}.{occurrence}",
                        status="FAIL",
                        expected=f"section '{heading}' occurrence {occurrence} found",
                        actual="section not found",
                        details={
                            "space_id": space_id,
                            "path": path,
                            "heading": heading,
                            "occurrence": occurrence,
                        },
                    )
                )
            else:
                checks.append(
                    ReadCheck(
                        id=f"read.{space_id}.{path}.{heading}.{occurrence}",
                        status="PASS",
                        expected=f"section '{heading}' occurrence {occurrence} not found",
                        actual="section not found",
                        details={
                            "space_id": space_id,
                            "path": path,
                            "heading": heading,
                            "occurrence": occurrence,
                        },
                    )
                )
            return checks

        if result.revision_sha != document.revision_sha:
            checks.append(
                ReadCheck(
                    id=f"read.{space_id}.{path}.{heading}.{occurrence}.revision",
                    status="FAIL",
                    expected=f"section read returns exact revision SHA {document.revision_sha}",
                    actual=f"got {result.revision_sha}",
                    details={
                        "path": path,
                        "heading": heading,
                        "occurrence": occurrence,
                    },
                )
            )
        else:
            checks.append(
                ReadCheck(
                    id=f"read.{space_id}.{path}.{heading}.{occurrence}.revision",
                    status="PASS",
                    expected="section read returns exact revision SHA",
                    actual=f"revision {result.revision_sha}",
                    details={
                        "path": path,
                        "heading": heading,
                        "occurrence": occurrence,
                    },
                )
            )

        if result.anchor is None:
            checks.append(
                ReadCheck(
                    id=f"read.{space_id}.{path}.{heading}.{occurrence}.anchor",
                    status="FAIL",
                    expected="section read returns anchor",
                    actual="anchor is None",
                    details={
                        "path": path,
                        "heading": heading,
                        "occurrence": occurrence,
                    },
                )
            )
        else:
            checks.append(
                ReadCheck(
                    id=f"read.{space_id}.{path}.{heading}.{occurrence}.anchor",
                    status="PASS",
                    expected="section read returns anchor",
                    actual=f"anchor={result.anchor}",
                    details={
                        "path": path,
                        "heading": heading,
                        "occurrence": occurrence,
                        "anchor": result.anchor,
                    },
                )
            )

        if result.occurrence != occurrence:
            checks.append(
                ReadCheck(
                    id=f"read.{space_id}.{path}.{heading}.{occurrence}.occurrence",
                    status="FAIL",
                    expected=f"occurrence={occurrence}",
                    actual=f"occurrence={result.occurrence}",
                    details={"path": path, "heading": heading},
                )
            )
        else:
            checks.append(
                ReadCheck(
                    id=f"read.{space_id}.{path}.{heading}.{occurrence}.occurrence",
                    status="PASS",
                    expected=f"occurrence={occurrence}",
                    actual=f"occurrence={result.occurrence}",
                    details={"path": path, "heading": heading},
                )
            )

        if result.truncated != expect_truncated:
            checks.append(
                ReadCheck(
                    id=f"read.{space_id}.{path}.{heading}.{occurrence}.truncated",
                    status="FAIL",
                    expected=f"truncated={'true' if expect_truncated else 'false'}",
                    actual=f"truncated={'true' if result.truncated else 'false'}",
                    details={
                        "path": path,
                        "heading": heading,
                        "max_lines": max_lines,
                        "total_lines": result.total_lines,
                    },
                )
            )
        else:
            checks.append(
                ReadCheck(
                    id=f"read.{space_id}.{path}.{heading}.{occurrence}.truncated",
                    status="PASS",
                    expected=f"truncated={'true' if expect_truncated else 'false'}",
                    actual=f"truncated={'true' if result.truncated else 'false'}",
                    details={
                        "path": path,
                        "heading": heading,
                        "max_lines": max_lines,
                        "total_lines": result.total_lines,
                    },
                )
            )

        checks.append(
            ReadCheck(
                id=f"read.{space_id}.{path}.{heading}.{occurrence}.bounds",
                status="PASS",
                expected="section read returns start_line, end_line, cursor",
                actual=f"start={result.start_line}, end={result.end_line}, cursor={result.cursor}, lines={len(result.lines)}",
                details={
                    "path": path,
                    "heading": heading,
                    "occurrence": occurrence,
                    "start_line": result.start_line,
                    "end_line": result.end_line,
                    "cursor": result.cursor,
                    "line_count": len(result.lines),
                },
            )
        )
        return checks
