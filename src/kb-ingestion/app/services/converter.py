"""Conversion pipeline and dry-run report (KBI-106/108)."""

from __future__ import annotations

import uuid
from pathlib import Path

from ..adapters.object_store import ObjectStore
from ..parsers import extraction_router
from ..parsers.base import ParserError
from ..schemas.convert import AttachmentManifestEntry, ConvertRunRequest, DryRunReport
from ..services.media_processor import classify_image, requires_verification
from ..validators import front_matter


class ConversionError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class ConversionService:
    def __init__(self, store: ObjectStore) -> None:
        self._store = store

    def run_dry_convert(self, request: ConvertRunRequest) -> DryRunReport:
        staged = self._store.get_staged(request.space_id, request.client_id, request.object_id)
        raw = self._store.get(request.space_id, request.client_id, request.object_id)
        if staged is None or raw is None:
            raise ConversionError("OBJECT_NOT_FOUND", "staged object not found", http_status=404)
        filename = Path(request.source_path).name
        try:
            parsed = extraction_router.extract(filename, staged.media_type, raw)
        except ParserError as exc:
            raise ConversionError(exc.code, exc.message) from exc
        try:
            front_matter.validate_source_path(request.source_path)
        except front_matter.FrontMatterError as exc:
            raise ConversionError(exc.code, exc.message) from exc

        attachments: list[AttachmentManifestEntry] = []
        blockers: list[dict[str, str]] = []
        markdown_parts = [parsed.markdown_body] if parsed.markdown_body else []
        for media in parsed.embedded_media:
            classified = classify_image(media.filename, media.data, media.media_type)
            media_object_id = uuid.uuid4().hex
            self._store.put(
                request.space_id,
                request.client_id,
                media_object_id,
                classified.data,
                classified.media_type,
            )
            alt_text = Path(classified.filename).stem.replace("-", " ")
            automatic = True
            verification_status = "pending" if requires_verification(classified.media_class) else None
            entry = AttachmentManifestEntry(
                object_id=media_object_id,
                media_type=classified.media_type,
                media_class=classified.media_class,
                alt_text=alt_text,
                automatic=automatic,
                verification_status=verification_status,
            )
            attachments.append(entry)
            if classified.media_class == "decorative":
                continue
            markdown_parts.append(
                f"![{alt_text}](attachment://{media_object_id})",
            )
            if verification_status == "pending":
                blockers.append(
                    {
                        "code": "MEDIA_VERIFICATION_PENDING",
                        "detail": f"{classified.filename} requires human verification",
                    }
                )

        markdown = "\n\n".join(part for part in markdown_parts if part).strip() or "(empty document)"
        try:
            draft = front_matter.build_front_matter_draft(
                source_path=request.source_path,
                markdown_body=markdown,
                attachments=attachments,
                ownership_mode=request.ownership_mode,
                origin=request.origin,
                staged_sha256=staged.sha256,
                staged_object_id=request.object_id,
                staged_version_id=staged.version_id,
            )
        except front_matter.FrontMatterError as exc:
            raise ConversionError(exc.code, exc.message) from exc

        status = "blocked" if blockers else "ready"
        path_map = {request.source_path: request.object_id}
        return DryRunReport(
            path_map=path_map,
            markdown=markdown,
            attachments=attachments,
            blockers=blockers,
            losses=parsed.losses,
            errors=[],
            front_matter_draft=draft,
            status=status,
        )