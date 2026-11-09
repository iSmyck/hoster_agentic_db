"""OpenAPI parse, operationId uniqueness and mutation header checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class OpenApiChecker:
    """Lightweight OpenAPI checks without an external OpenAPI parser."""

    def __init__(self, contracts_dir: Path) -> None:
        self.contracts_dir = contracts_dir
        self.openapi: dict[str, Any] = self._load("openapi.yaml")
        self.agent_tools: dict[str, Any] = self._load("agent-tools.yaml")

    def _load(self, filename: str) -> dict[str, Any]:
        path = self.contracts_dir / filename
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def operation_ids(self) -> list[tuple[str, str, str]]:
        """Return [(path, method, operationId)] for every operation."""
        found: list[tuple[str, str, str]] = []
        paths = self.openapi.get("paths", {})
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, operation in methods.items():
                if method.startswith("x-") or not isinstance(operation, dict):
                    continue
                op_id = operation.get("operationId")
                if op_id:
                    found.append((str(path), method.lower(), op_id))
        return found

    def duplicate_operation_ids(self) -> list[tuple[str, list[tuple[str, str]]]]:
        """Return groups of duplicate operationIds with their locations."""
        from collections import defaultdict

        by_id: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for path, method, op_id in self.operation_ids():
            by_id[op_id].append((path, method))
        return [(op_id, locs) for op_id, locs in by_id.items() if len(locs) > 1]

    def mutation_operations(self) -> list[tuple[str, str, dict[str, Any]]]:
        """Return [(path, method, operation)] for mutating methods."""
        mutating = {"post", "put", "patch", "delete"}
        ops: list[tuple[str, str, dict[str, Any]]] = []
        paths = self.openapi.get("paths", {})
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, operation in methods.items():
                if method.lower() in mutating and isinstance(operation, dict):
                    ops.append((str(path), method.lower(), operation))
        return ops

    def _resolve_parameter(self, param: Any) -> dict[str, Any] | None:
        """Resolve a parameter item, which may be a $ref, to a parameter dict."""
        if not isinstance(param, dict):
            return None
        if "$ref" in param and isinstance(param["$ref"], str):
            try:
                return self._resolve_local_ref(param["$ref"], {"openapi.yaml": self.openapi})
            except Exception:  # pragma: no cover
                return None
        return param

    def idempotency_operations(self) -> set[str]:
        """Return operationIds that the contract invariants say require idempotency."""
        invariants = self.openapi.get("x-contract-invariants", [])
        for inv in invariants:
            if isinstance(inv, dict) and inv.get("id") == "BODY_HEADER_IDEMPOTENCY":
                return set(inv.get("operations", []))
        return set()

    def missing_idempotency_header(self) -> list[tuple[str, str, str | None]]:
        """Return operations requiring Idempotency-Key that do not declare it."""
        required_ops = self.idempotency_operations()
        missing: list[tuple[str, str, str | None]] = []
        for path, method, operation in self.operation_ids():
            op_id = operation
            if op_id not in required_ops:
                continue
            op = self.openapi["paths"][path].get(method, {})
            params = op.get("parameters", [])
            required_headers = set()
            for p in params:
                resolved = self._resolve_parameter(p)
                if resolved and resolved.get("in") == "header" and resolved.get("required"):
                    required_headers.add(resolved.get("name"))
            if "Idempotency-Key" not in required_headers:
                missing.append((path, method, op_id))
        return missing

    def resolve_refs(self) -> list[tuple[str, str, Exception | None]]:
        """Walk OpenAPI and agent-tools files, collecting every local/cross-file $ref target."""
        results: list[tuple[str, str, Exception | None]] = []
        targets: set[str] = set()

        def collect_refs(node: Any, path: str) -> None:
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "$ref" and isinstance(v, str):
                        if v.startswith("#") or v.startswith("./openapi.yaml#"):
                            targets.add(v)
                    collect_refs(v, f"{path}/{k}")
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    collect_refs(item, f"{path}[{i}]")

        collect_refs(self.openapi, "openapi.yaml")
        collect_refs(self.agent_tools, "agent-tools.yaml")

        # Resolve local JSON/YAML pointers naively against loaded documents.
        documents = {
            "openapi.yaml": self.openapi,
            "agent-tools.yaml": self.agent_tools,
        }
        for ref in sorted(targets):
            try:
                self._resolve_local_ref(ref, documents)
                results.append(("openapi/agent-tools", ref, None))
            except Exception as exc:
                results.append(("openapi/agent-tools", ref, exc))
        return results

    def _resolve_local_ref(
        self, ref: str, documents: dict[str, Any]
    ) -> Any:  # pragma: no cover
        if "#" not in ref:
            raise ValueError(f"Unsupported ref: {ref}")
        file_part, pointer = ref.split("#", 1)
        if file_part and file_part not in ("./openapi.yaml", "openapi.yaml"):
            raise ValueError(f"Cross-file ref not resolved here: {ref}")
        doc = documents["openapi.yaml"]
        if not pointer.startswith("/"):
            raise ValueError(f"Invalid JSON pointer: {pointer}")
        parts = pointer[1:].split("/")
        node = doc
        for part in parts:
            part = part.replace("~0", "~").replace("~1", "/")
            if isinstance(node, dict):
                if part not in node:
                    raise KeyError(part)
                node = node[part]
            elif isinstance(node, list):
                node = node[int(part)]
            else:
                raise TypeError(type(node))
        return node

    def agent_tool_operation_ids(self) -> set[str]:
        """Return operationIds declared in agent-tools.yaml."""
        ids: set[str] = set()
        tools = self.agent_tools.get("tools", [])
        for tool in tools:
            if isinstance(tool, dict):
                ids.add(tool.get("operation_id") or tool.get("operationId"))
        return {i for i in ids if i}

    def bounded_agent_operation_ids(self) -> set[str]:
        """Return operationIds that accept boundedAgentCredential security."""
        ids: set[str] = set()
        for path, method, operation in self.operation_ids():
            op = self.openapi["paths"][path].get(method, {})
            security = op.get("security", [])
            for sec in security:
                if isinstance(sec, dict) and "boundedAgentCredential" in sec:
                    ids.add(operation)
                    break
        return ids
