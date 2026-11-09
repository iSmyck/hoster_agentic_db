"""Shared domain error for retrieval/indexing services."""

from __future__ import annotations


class RetrievalServiceError(Exception):
    """Domain error raised by retrieval/indexing services."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
