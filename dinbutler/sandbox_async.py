"""Async E2B-compatible Sandbox class."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Dict, List, Union, Iterator, Callable
from concurrent.futures import ThreadPoolExecutor

from dinbutler.sandbox import Sandbox, Filesystem, Commands, Pty
from dinbutler.models.sandbox import SandboxInfo
from dinbutler.models.filesystem import EntryInfo, WriteInfo
from dinbutler.models.commands import CommandResult, CommandHandle, ProcessInfo, PtySize
from dinbutler.services.pty import PtyHandle

logger = logging.getLogger(__name__)

# Thread pool for running sync operations
_executor = ThreadPoolExecutor(max_workers=10)


async def _run_sync(func, *args, **kwargs):
    """Run synchronous function in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, lambda: func(*args, **kwargs))


class AsyncFilesystem:
    """Async filesystem operations."""

    def __init__(self, sync_fs: Filesystem):
        self._sync = sync_fs

    async def read(
        self,
        path: str,
        format: str = "text",
        user: Optional[str] = None,
        request_timeout: Optional[float] = None,
    ) -> Union[str, bytes]:
        return await _run_sync(self._sync.read, path, format, user, request_timeout)

    async def write(
        self,
        path: str,
        data: Union[str, bytes],
        user: Optional[str] = None,
        request_timeout: Optional[float] = None,
    ) -> WriteInfo:
        return await _run_sync(self._sync.write, path, data, user, request_timeout)

    async def list(
        self,
        path: str,
        depth: int = 1,
        user: Optional[str] = None,
        request_timeout: Optional[float] = None,
    ) -> List[EntryInfo]:
        return await _run_sync(self._sync.list, path, depth, user, request_timeout)

    async def exists(self, path: str, user: Optional[str] = None) -> bool:
        return await _run_sync(self._sync.exists, path, user)

    async def get_info(self, path: str, user: Optional[str] = None) -> EntryInfo:
        return await _run_sync(self._sync.get_info, path, user)

    async def remove(self, path: str, user: Optional[str] = None) -> None:
        return await _run_sync(self._sync.remove, path, user)


class AsyncCommands:
    """Async command execution."""

    def __init__(self, sync_cmds: Commands):
        self._sync = sync_cmds

    async def run(
        self,
        cmd: str,
        background: bool = False,
        envs: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        user: Optional[str] = None,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
        timeout: float = 60,
        request_timeout: Optional[float] = None,
    ) -> Union[CommandResult, CommandHandle]:
        return await _run_sync(
            self._sync.run, cmd, background, envs, cwd, user,
            on_stdout, on_stderr, timeout, request_timeout
        )

    async def list(self, request_timeout: Optional[float] = None) -> List[ProcessInfo]:
        return await _run_sync(self._sync.list, request_timeout)

    async def kill(
        self,
        pid: int,
        signal: str = "KILL",
        request_timeout: Optional[float] = None,
    ) -> bool:
        return await _run_sync(self._sync.kill, pid, signal, request_timeout)


class AsyncPty:
    """Async PTY operations."""

    def __init__(self, sync_pty: Pty):
        self._sync = sync_pty

    async def create(
        self,
        size: Optional[PtySize] = None,
        user: Optional[str] = None,
        cwd: Optional[str] = None,
        envs: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 60,
        request_timeout: Optional[float] = None,
    ) -> PtyHandle:
        return await _run_sync(
            self._sync.create, size, user, cwd, envs, timeout, request_timeout
        )

    async def kill(self, pid: int, request_timeout: Optional[float] = None) -> bool:
        return await _run_sync(self._sync.kill, pid, request_timeout)


class AsyncSandbox:
    """Async E2B-compatible Sandbox.

    Usage:
        sandbox = await AsyncSandbox.create(template="python")
        result = await sandbox.commands.run("python --version")
        await sandbox.kill()

        # Or with context manager
        async with await AsyncSandbox.create() as sandbox:
            await sandbox.commands.run("echo hello")
    """

    def __init__(self, sync_sandbox: Sandbox):
        self._sync = sync_sandbox
        self.files = AsyncFilesystem(sync_sandbox.files)
        self.commands = AsyncCommands(sync_sandbox.commands)
        self.pty = AsyncPty(sync_sandbox.pty)

    @property
    def sandbox_id(self) -> str:
        return self._sync.sandbox_id

    @classmethod
    async def create(
        cls,
        template: str = "default",
        timeout: int = 300,
        envs: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> "AsyncSandbox":
        """Create a new sandbox asynchronously."""
        sync_sandbox = await _run_sync(
            Sandbox.create, template, timeout, envs, metadata, **kwargs
        )
        return cls(sync_sandbox)

    @classmethod
    async def connect(cls, sandbox_id: str, **kwargs) -> "AsyncSandbox":
        """Connect to an existing sandbox."""
        sync_sandbox = await _run_sync(Sandbox.connect, sandbox_id, **kwargs)
        return cls(sync_sandbox)

    @classmethod
    async def list(cls, **kwargs) -> List[SandboxInfo]:
        """List all sandboxes."""
        return await _run_sync(Sandbox.list, **kwargs)

    async def kill(self, **kwargs) -> bool:
        """Kill this sandbox."""
        return await _run_sync(self._sync.kill, **kwargs)

    async def is_running(self, **kwargs) -> bool:
        """Check if sandbox is running."""
        return await _run_sync(self._sync.is_running, **kwargs)

    async def set_timeout(self, timeout: int, **kwargs) -> None:
        """Update sandbox timeout."""
        return await _run_sync(self._sync.set_timeout, timeout, **kwargs)

    async def get_info(self, **kwargs) -> SandboxInfo:
        """Get sandbox information."""
        return await _run_sync(self._sync.get_info, **kwargs)

    async def __aenter__(self) -> "AsyncSandbox":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.kill()

    def __repr__(self) -> str:
        return f"AsyncSandbox(id={self.sandbox_id})"
