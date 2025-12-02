"""Colima E2B - Local E2B-compatible sandbox using Colima/Docker."""

from dinbutler.sandbox import Sandbox
from dinbutler.sandbox_async import AsyncSandbox
from dinbutler.models.sandbox import SandboxInfo, SandboxState, SandboxQuery
from dinbutler.models.filesystem import EntryInfo, WriteInfo, FileType, FilesystemEvent, FilesystemEventType
from dinbutler.models.commands import CommandResult, CommandHandle, ProcessInfo, PtySize
from dinbutler.exceptions import (
    SandboxException,
    TimeoutException,
    NotFoundException,
    InvalidArgumentException,
    CommandExitException,
    TemplateException,
    DockerException,
    ColimaException,
)

__version__ = "0.1.0"
__all__ = [
    # Main classes
    "Sandbox",
    "AsyncSandbox",
    # Sandbox models
    "SandboxInfo",
    "SandboxState",
    "SandboxQuery",
    # Filesystem models
    "EntryInfo",
    "WriteInfo",
    "FileType",
    "FilesystemEvent",
    "FilesystemEventType",
    # Command models
    "CommandResult",
    "CommandHandle",
    "ProcessInfo",
    "PtySize",
    # Exceptions
    "SandboxException",
    "TimeoutException",
    "NotFoundException",
    "InvalidArgumentException",
    "CommandExitException",
    "TemplateException",
    "DockerException",
    "ColimaException",
]
