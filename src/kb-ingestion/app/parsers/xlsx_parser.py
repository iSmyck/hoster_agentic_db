"""Spreadsheet to markdown table extractor."""

from __future__ import annotations

import io
import zipfile

from .base import ParserError, ParseResult
from .ooxml import ooxml_security_check


def extract(filename: str, data: bytes) -> ParseResult:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ParserError("UNSUPPORTED_FORMAT", "xlsx is not a valid zip archive") from exc
    with zf:
        ooxml_security_check(zf)
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ParserError("UNSUPPORTED_FORMAT", "xlsx extractor unavailable") from exc
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        raise ParserError("UNSUPPORTED_FORMAT", "xlsx is not readable") from exc
    sheet = workbook.active
    if sheet is None:
        return ParseResult(markdown_body="(empty spreadsheet)", losses=[{"kind": "empty_sheet", "detail": "no active sheet"}])
    rows: list[list[str]] = []
    for row in sheet.iter_rows(values_only=True):
        cells = ["" if cell is None else str(cell) for cell in row]
        if any(cells):
            rows.append(cells)
    if not rows:
        return ParseResult(markdown_body="(empty spreadsheet)")
    header = rows[0]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    for row in rows[1:]:
        padded = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(padded[: len(header)]) + " |")
    return ParseResult(markdown_body="\n".join(lines))