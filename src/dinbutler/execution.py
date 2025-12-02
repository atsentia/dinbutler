"""Execution result classes for sandbox code execution."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionError:
    """Represents an error that occurred during code execution."""

    name: str
    value: str
    traceback: str

    def __str__(self) -> str:
        return f"{self.name}: {self.value}\n{self.traceback}"


@dataclass
class Result:
    """Represents a single output result from code execution."""

    text: str | None = None
    html: str | None = None
    markdown: str | None = None
    data: dict[str, Any] | None = None

    @property
    def is_empty(self) -> bool:
        """Check if the result is empty."""
        return self.text is None and self.html is None and self.markdown is None


@dataclass
class Execution:
    """Represents the result of a code execution in the sandbox."""

    results: list[Result] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    error: ExecutionError | None = None
    exit_code: int = 0

    @property
    def text(self) -> str:
        """Get the combined text output from all results."""
        texts = [r.text for r in self.results if r.text]
        return "\n".join(texts)

    @property
    def html(self) -> str | None:
        """Get the first HTML result."""
        for r in self.results:
            if r.html:
                return r.html
        return None

    @property
    def markdown(self) -> str | None:
        """Get the first markdown result."""
        for r in self.results:
            if r.markdown:
                return r.markdown
        return None

    def __bool__(self) -> bool:
        """Execution is truthy if there was no error."""
        return self.error is None
