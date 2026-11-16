"""Conversion pipeline and dry-run report (KBI-106/108)."""

from __future__ import annotations

import uuid
from pathlib import Path

from ..adapters.object_store import ObjectStore, ObjectStoreError
from ..parsers import extraction_router
from ..parsers.base import ParserError
from ..schemas.convert import (
    AttachmentManifestEntry,
    ConvertRunRequest,
    CorrectionTaskDraft,
    DryRunReport,
)
from ..services.converted_corpus import ConvertedCorpus, ConvertedDocument
from ..services.media_processor import classify_image, requires_verification
from ..services.mermaid_route import MermaidRoute
from ..validators import front_matter
from ..validators.data_barrier import DataBarrierError, enforce_data_barrier


class ConversionError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class ConversionService:
    def __init__(
        self,
        store: ObjectStore,
        corpus: ConvertedCorpus | None = None,
        mermaid_route: MermaidRoute | None = None,
    ) -> None:
        self._store = store
        self._corpus = corpus or ConvertedCorpus()
        self._mermaid = mermaid_route or MermaidRoute()

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
        errors = list(parsed.errors)
        markdown_parts = [parsed.markdown_body] if parsed.markdown_body else []
        empty_placeholders = {
            "",
            "(empty pdf)",
            "(empty document)",
            "(empty docx)",
            "(empty pptx)",
            "(empty html document)",
        }
        for media in parsed.embedded_media:
            primary_asset = (
                parsed.markdown_body.strip() in empty_placeholders
                and len(parsed.embedded_media) == 1
                and Path(media.filename).name == filename
            )
            classified = classify_image(
                media.filename,
                media.data,
                media.media_type,
                primary_asset=primary_asset,
            )
            media_object_id = uuid.uuid4().hex
            staged_media = self._store.put(
                request.space_id,
                request.client_id,
                media_object_id,
                classified.data,
                classified.media_type,
            )
            alt_text = Path(classified.filename).stem.replace("-", " ") or "image"
            mermaid_source = None
            mermaid_status = "none"
            mermaid_error = None
            if classified.diagram_candidate:
                converted = self._mermaid.convert_diagram(classified.filename, classified.data)
                mermaid_source = converted.source
                mermaid_status = converted.status
                mermaid_error = converted.error
            pending = requires_verification(classified.media_class) and mermaid_status != "validated"
            verification_status: str = "pending" if pending else "not_required"
            entry = AttachmentManifestEntry(
                object_id=staged_media.object_id,
                version=staged_media.version_id,
                sha256=staged_media.sha256,
                size=staged_media.size,
                media_type=staged_media.media_type,
                source_ref=f"embedded:{classified.filename}",
                media_class=classified.media_class,
                verification_status=verification_status,
                alt_text=alt_text,
                automatic=True,
                diagram_candidate=classified.diagram_candidate,
                mermaid_source=mermaid_source,
                mermaid_status=mermaid_status,  # type: ignore[arg-type]
            )
            attachments.append(entry)
            if classified.media_class == "decorative":
                continue
            if mermaid_status == "validated" and mermaid_source:
                markdown_parts.append(f"```mermaid\n{mermaid_source}\n```")
            else:
                markdown_parts.append(f"![{alt_text}](attachment://{staged_media.object_id})")
            if mermaid_status == "invalid":
                errors.append(
                    {
                        "code": "MERMAID_INVALID",
                        "detail": mermaid_error or "mermaid validation failed",
                    }
                )
            if pending:
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
        except front_matter.FrontMatterError as extra:
            raise ConversionError(extra.code, extra.message) from extra

        try:
            enforce_data_barrier(
                data_profile=request.data_profile,
                text=markdown,
                legal_basis=request.legal_basis,
                inference_provider=request.inference_provider,
                document_path=request.source_path,
                document_id=str(draft["id"]),
            )
        except DataBarrierError as barrier:
            if barrier.code != "PII_BLOCKED":
                raise ConversionError(barrier.code, barrier.message) from barrier
            blockers.append({"code": "PII_REVIEW_REQUIRED", "detail": barrier.message})

        correction_tasks = _build_correction_tasks(
            blockers=blockers,
            source_path=request.source_path,
            document_id=str(draft["id"]),
        )
        status = "blocked" if blockers else "ready"
        path_map = {request.source_path: request.object_id}
        markdown_object_id = uuid.uuid4().hex
        try:
            self._store.put(
                request.space_id,
                request.client_id,
                markdown_object_id,
                markdown.encode("utf-8"),
                "text/markdown",
            )
            self._corpus.put(
                ConvertedDocument(
                    markdown_object_id=markdown_object_id,
                    source_object_id=request.object_id,
                    space_id=request.space_id,
                    client_id=request.client_id,
                    source_path=request.source_path,
                    status=status,
                    markdown=markdown,
                    attachments=list(attachments),
                    front_matter_draft=draft,
                )
            )
        except ObjectStoreError as exc:
            raise ConversionError("PERSIST_FAILED", exc.message, http_status=500) from exc
        return DryRunReport(
            path_map=path_map,
            markdown_object_id=markdown_object_id,
            markdown=markdown,
            attachments=attachments,
            blockers=blockers,
            losses=parsed.losses,
            errors=errors,
            front_matter_draft=draft,
            correction_tasks=correction_tasks,
            status=status,
        )


def _build_correction_tasks(
    *,
    blockers: list[dict[str, str]],
    source_path: str,
    document_id: str,
) -> list[CorrectionTaskDraft]:
    tasks: list[CorrectionTaskDraft] = []
    for blocker in blockers:
        tasks.append(
            CorrectionTaskDraft(
                blocker_code=blocker["code"],
                document_path=source_path,
                document_id=document_id,
                reason=blocker["detail"],
            )
        )
    return tasks