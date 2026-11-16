"""Vision LLM port for diagram→Mermaid (KBI.5.2). Live providers are not called."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

GOLDEN_MERMAID: dict[str, str] = {
    "flowchart-diagram.png": "flowchart TD\n  A-->B",
    "wiring-schematic.png": "flowchart LR\n  X-->Y",
}


class VisionLLMError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class VisionLLM(ABC):
    configured: bool

    @abstractmethod
    def generate_mermaid(self, filename: str, data: bytes) -> str:
        """Return Mermaid source for a diagram image."""

    @abstractmethod
    def golden_pass(self) -> bool:
        """True when golden fixtures match generated source."""


class StubVisionLLM(VisionLLM):
    def __init__(self, *, configured: bool = False) -> None:
        self.configured = configured
        self.fail_message: str | None = None
        self.invalid_next: bool = False
        self.calls: list[str] = []

    def generate_mermaid(self, filename: str, data: bytes) -> str:
        del data
        self.calls.append(filename)
        if self.fail_message:
            raise VisionLLMError(self.fail_message)
        if self.invalid_next:
            self.invalid_next = False
            return "this is not mermaid INVALID"
        name = Path(filename).name.lower()
        for key, source in GOLDEN_MERMAID.items():
            if name == key or key in name:
                return source
        return "flowchart TD\n  A-->B"

    def golden_pass(self) -> bool:
        if not self.configured:
            return False
        for filename, expected in GOLDEN_MERMAID.items():
            if self.generate_mermaid(filename, b"") != expected:
                return False
        return True
