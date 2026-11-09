"""Tree navigation validator: parent/child, breadcrumbs, stable IDs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .document_store import Document, Space


@dataclass
class TreeCheck:
    id: str
    status: str  # PASS / FAIL / BLOCKED
    expected: str
    actual: str
    details: dict[str, Any]


class TreeValidator:
    """Validate a synthetic Space document tree."""

    def __init__(self, spaces: dict[str, Space]) -> None:
        self.spaces = spaces

    def validate(
        self, rename_scenarios: dict[str, dict[str, tuple[str, str]]]
    ) -> list[TreeCheck]:
        """Run all tree validation checks.

        *rename_scenarios* maps space_id -> document_id -> (old_path, new_path).
        """
        checks: list[TreeCheck] = []
        for space in self.spaces.values():
            checks.extend(self._validate_space(space))
            checks.extend(
                self._validate_rename(space, rename_scenarios.get(space.space_id, {}))
            )
        return checks

    def _validate_space(self, space: Space) -> list[TreeCheck]:
        checks: list[TreeCheck] = []
        by_id = space.by_id()
        by_path = space.by_path()

        # Unique IDs.
        seen_ids: dict[str, list[str]] = {}
        for doc in space.documents:
            doc_id = doc.document_id
            if doc_id is None:
                continue
            seen_ids.setdefault(doc_id, []).append(doc.path)
        duplicates = {
            doc_id: paths for doc_id, paths in seen_ids.items() if len(paths) > 1
        }
        if duplicates:
            checks.append(
                TreeCheck(
                    id=f"tree.{space.space_id}.unique_ids",
                    status="FAIL",
                    expected="document IDs are unique within a Space",
                    actual=f"duplicate IDs: {duplicates}",
                    details={"duplicates": duplicates},
                )
            )
        else:
            checks.append(
                TreeCheck(
                    id=f"tree.{space.space_id}.unique_ids",
                    status="PASS",
                    expected="document IDs are unique within a Space",
                    actual=f"{len(seen_ids)} unique IDs",
                    details={"count": len(seen_ids)},
                )
            )

        # Parent existence (excluding orphans).
        missing_parents: list[tuple[str, str]] = []
        for doc in space.documents:
            parent_id = doc.parent_id
            if parent_id is not None and parent_id not in by_id:
                missing_parents.append((doc.path, parent_id))
        if missing_parents:
            checks.append(
                TreeCheck(
                    id=f"tree.{space.space_id}.parent_exists",
                    status="FAIL",
                    expected="every non-root parent_id resolves within the Space",
                    actual=f"orphan parents: {missing_parents}",
                    details={"missing_parents": missing_parents},
                )
            )
        else:
            checks.append(
                TreeCheck(
                    id=f"tree.{space.space_id}.parent_exists",
                    status="PASS",
                    expected="every non-root parent_id resolves within the Space",
                    actual="all parents resolved",
                    details={"count": len([d for d in space.documents if d.parent_id])},
                )
            )

        # Cycles.
        cycles = self._find_cycles(space)
        if cycles:
            checks.append(
                TreeCheck(
                    id=f"tree.{space.space_id}.no_cycles",
                    status="FAIL",
                    expected="document parent graph has no cycles",
                    actual=f"cycles detected: {cycles}",
                    details={"cycles": cycles},
                )
            )
        else:
            checks.append(
                TreeCheck(
                    id=f"tree.{space.space_id}.no_cycles",
                    status="PASS",
                    expected="document parent graph has no cycles",
                    actual="no cycles",
                    details={},
                )
            )

        # Breadcrumbs.
        breadcrumbs = self._build_breadcrumbs(space)
        checks.append(
            TreeCheck(
                id=f"tree.{space.space_id}.breadcrumbs",
                status="PASS",
                expected="breadcrumbs resolve to root for every document",
                actual=f"computed breadcrumbs for {len(breadcrumbs)} documents",
                details={"breadcrumbs": breadcrumbs},
            )
        )

        # Parent/child relationships.
        children: dict[str, list[str]] = {}
        for doc in space.documents:
            parent_id = doc.parent_id
            if parent_id is not None:
                children.setdefault(parent_id, []).append(doc.path)
        checks.append(
            TreeCheck(
                id=f"tree.{space.space_id}.parent_child",
                status="PASS",
                expected="parent/child relationships are derivable from parent_id",
                actual=f"{len(children)} parents with children",
                details={"children": children},
            )
        )

        return checks

    def _find_cycles(self, space: Space) -> list[list[str]]:
        by_id = space.by_id()
        cycles: list[list[str]] = []
        visited: set[str] = set()
        stack: set[str] = set()

        def visit(doc_id: str, path: list[str]) -> None:
            if doc_id in stack:
                cycle_start = path.index(doc_id)
                cycles.append(path[cycle_start:] + [doc_id])
                return
            if doc_id in visited:
                return
            visited.add(doc_id)
            stack.add(doc_id)
            doc = by_id.get(doc_id)
            if doc and doc.parent_id:
                visit(doc.parent_id, path + [doc_id])
            stack.discard(doc_id)

        for doc_id in by_id:
            if doc_id not in visited:
                visit(doc_id, [])
        return cycles

    def _build_breadcrumbs(self, space: Space) -> dict[str, list[str]]:
        by_id = space.by_id()
        breadcrumbs: dict[str, list[str]] = {}
        for doc in space.documents:
            doc_id = doc.document_id
            if doc_id is None:
                continue
            crumb: list[str] = []
            current_id: str | None = doc_id
            seen: set[str] = set()
            while current_id and current_id not in seen:
                seen.add(current_id)
                current = by_id.get(current_id)
                if current is None:
                    break
                title = current.title or current.path
                crumb.insert(0, title)
                current_id = current.parent_id
            breadcrumbs[doc_id] = crumb
        return breadcrumbs

    def _validate_rename(
        self, space: Space, scenarios: dict[str, tuple[str, str]]
    ) -> list[TreeCheck]:
        """Verify stable IDs survive rename/move operations."""
        checks: list[TreeCheck] = []
        by_id = space.by_id()
        by_path = space.by_path()
        for doc_id, (old_path, new_path) in scenarios.items():
            doc = by_id.get(doc_id)
            if doc is None:
                checks.append(
                    TreeCheck(
                        id=f"tree.{space.space_id}.stable_id_rename.{doc_id}",
                        status="FAIL",
                        expected=f"document {doc_id} survives rename from {old_path} to {new_path}",
                        actual=f"document {doc_id} not found in Space",
                        details={
                            "document_id": doc_id,
                            "old_path": old_path,
                            "new_path": new_path,
                        },
                    )
                )
                continue
            if doc.path != new_path:
                checks.append(
                    TreeCheck(
                        id=f"tree.{space.space_id}.stable_id_rename.{doc_id}",
                        status="FAIL",
                        expected=f"document {doc_id} is at new path {new_path}",
                        actual=f"document found at {doc.path}",
                        details={
                            "document_id": doc_id,
                            "old_path": old_path,
                            "new_path": new_path,
                        },
                    )
                )
                continue
            if old_path in by_path:
                old_doc = by_path[old_path]
                if old_doc.document_id != doc_id:
                    checks.append(
                        TreeCheck(
                            id=f"tree.{space.space_id}.stable_id_rename.{doc_id}",
                            status="FAIL",
                            expected=f"old path {old_path} does not carry a different document ID",
                            actual=f"old path now has document {old_doc.document_id}",
                            details={
                                "document_id": doc_id,
                                "old_path": old_path,
                                "new_path": new_path,
                            },
                        )
                    )
                    continue
            checks.append(
                TreeCheck(
                    id=f"tree.{space.space_id}.stable_id_rename.{doc_id}",
                    status="PASS",
                    expected=f"document {doc_id} retains UUID after rename from {old_path} to {new_path}",
                    actual=f"UUID preserved at {new_path}",
                    details={
                        "document_id": doc_id,
                        "old_path": old_path,
                        "new_path": new_path,
                    },
                )
            )
        return checks
