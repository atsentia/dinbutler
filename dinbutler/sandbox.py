"""E2B-compatible Sandbox class using local Colima/Docker."""

from __future__ import annotations

import logging
from typing import Optional, Dict, List, Union, Iterator, Callable, TYPE_CHECKING

from dinbutler.services.docker_client import get_docker_client
from dinbutler.services.sandbox_manager import SandboxManager, get_sandbox_manager
from dinbutler.services.filesystem import FilesystemService, get_filesystem_service
from dinbutler.services.commands import CommandsService, get_commands_service
from dinbutler.services.pty import PtyService, PtyHandle, get_pty_service
from dinbutler.models.sandbox import SandboxInfo, SandboxState
from dinbutler.models.filesystem import EntryInfo, WriteInfo, FilesystemEvent
from dinbutler.models.commands import CommandResult, CommandHandle, ProcessInfo, PtySize
from dinbutler.exceptions import SandboxException, NotFoundException

logger = logging.getLogger(__name__)


class Filesystem:
    """Filesystem operations for a sandbox."""

    def __init__(self, sandbox: "Sandbox"):
        self._sandbox = sandbox
        self._service = get_filesystem_service()

    @property
    def _sandbox_id(self) -> str:
        return self._sandbox.sandbox_id

    def read(
        self,
        path: str,
        format: str = "text",
        user: Optional[str] = None,
        request_timeout: Optional[float] = None,
    ) -> Union[str, bytes, Iterator[bytes]]:
        """Read file content."""
        return self._service.read(self._sandbox_id, path, format, user, request_timeout)

    def write(
        self,
        path: str,
        data: Union[str, bytes],
        user: Optional[str] = None,
        request_timeout: Optional[float] = None,
    ) -> WriteInfo:
        """Write content to file."""
        return self._service.write(self._sandbox_id, path, data, user, request_timeout)

    def list(
        self,
        path: str,
        depth: int = 1,
        user: Optional[str] = None,
        request_timeout: Optional[float] = None,
    ) -> List[EntryInfo]:
        """List directory contents."""
        return self._service.list(self._sandbox_id, path, depth, user, request_timeout)

    def exists(self, path: str, user: Optional[str] = None) -> bool:
        """Check if path exists."""
        return self._service.exists(self._sandbox_id, path, user)

    def get_info(self, path: str, user: Optional[str] = None) -> EntryInfo:
        """Get file/directory info."""
        return self._service.get_info(self._sandbox_id, path, user)

    def remove(self, path: str, user: Optional[str] = None) -> None:
        """Remove file or directory."""
        return self._service.remove(self._sandbox_id, path, user)

    def watch(
        self,
        path: str,
        on_change: Optional[Callable[[FilesystemEvent], None]] = None,
        recursive: bool = False,
    ):
        """Watch directory for changes."""
        return self._service.watch(self._sandbox_id, path, on_change, recursive)


class Commands:
    """Command execution for a sandbox."""

    def __init__(self, sandbox: "Sandbox"):
        self._sandbox = sandbox
        self._service = get_commands_service()

    @property
    def _sandbox_id(self) -> str:
        return self._sandbox.sandbox_id

    def run(
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
        """Run a command."""
        return self._service.run(
            self._sandbox_id, cmd, background, envs, cwd, user,
            on_stdout, on_stderr, timeout, request_timeout
        )

    def list(self, request_timeout: Optional[float] = None) -> List[ProcessInfo]:
        """List running processes."""
        return self._service.list(self._sandbox_id, request_timeout)

    def kill(
        self,
        pid: int,
        signal: str = "KILL",
        request_timeout: Optional[float] = None,
    ) -> bool:
        """Kill a process."""
        return self._service.kill(self._sandbox_id, pid, signal, request_timeout)

    def send_stdin(
        self,
        pid: int,
        data: str,
        request_timeout: Optional[float] = None,
    ) -> None:
        """Send data to process stdin."""
        return self._service.send_stdin(self._sandbox_id, pid, data, request_timeout)

    def connect(
        self,
        pid: int,
        timeout: Optional[float] = 60,
        request_timeout: Optional[float] = None,
    ) -> CommandHandle:
        """Connect to a running process."""
        return self._service.connect(self._sandbox_id, pid, timeout, request_timeout)


class Pty:
    """PTY operations for a sandbox."""

    def __init__(self, sandbox: "Sandbox"):
        self._sandbox = sandbox
        self._service = get_pty_service()

    @property
    def _sandbox_id(self) -> str:
        return self._sandbox.sandbox_id

    def create(
        self,
        size: Optional[PtySize] = None,
        user: Optional[str] = None,
        cwd: Optional[str] = None,
        envs: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 60,
        request_timeout: Optional[float] = None,
    ) -> PtyHandle:
        """Create a PTY session."""
        return self._service.create(
            self._sandbox_id, size, user, cwd, envs,
            timeout=timeout, request_timeout=request_timeout
        )

    def kill(
        self,
        pid: int,
        request_timeout: Optional[float] = None,
    ) -> bool:
        """Kill a PTY session."""
        return self._service.kill(self._sandbox_id, pid, request_timeout)


class Sandbox:
    """E2B-compatible Sandbox using local Colima/Docker.

    This class provides a drop-in replacement for E2B's Sandbox class,
    using local Docker containers via Colima instead of cloud VMs.

    Usage:
        # Create a sandbox
        sandbox = Sandbox.create(template="python")

        # Run commands
        result = sandbox.commands.run("python --version")
        print(result.stdout)

        # Work with files
        sandbox.files.write("/tmp/hello.py", "print('Hello!')")
        sandbox.commands.run("python /tmp/hello.py")

        # Cleanup
        sandbox.kill()

        # Or use context manager
        with Sandbox.create() as sandbox:
            sandbox.commands.run("echo 'Hello World'")
    """

    def __init__(
        self,
        sandbox_id: str,
        info: Optional[SandboxInfo] = None,
    ):
        """Initialize sandbox instance.

        Don't call directly - use Sandbox.create() or Sandbox.connect().
        """
        self._sandbox_id = sandbox_id
        self._info = info
        self._manager = get_sandbox_manager()

        # Initialize modules
        self.files = Filesystem(self)
        self.commands = Commands(self)
        self.pty = Pty(self)

    @property
    def sandbox_id(self) -> str:
        """Get the sandbox ID."""
        return self._sandbox_id

    @classmethod
    def create(
        cls,
        template: str = "default",
        timeout: int = 300,
        envs: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> "Sandbox":
        """Create a new sandbox.

        Args:
            template: Template name ("default", "python", "node") or Docker image.
            timeout: Sandbox timeout in seconds (default 5 minutes).
            envs: Environment variables for the sandbox.
            metadata: Custom metadata labels.
            **kwargs: Additional arguments (ignored for compatibility).

        Returns:
            New Sandbox instance.

        Raises:
            SandboxException: If creation fails.
        """
        manager = get_sandbox_manager()
        info = manager.create(template, timeout, envs, metadata)
        logger.info(f"Created sandbox {info.sandbox_id}")
        return cls(info.sandbox_id, info)

    @classmethod
    def connect(cls, sandbox_id: str, **kwargs) -> "Sandbox":
        """Connect to an existing sandbox.

        Args:
            sandbox_id: The sandbox ID to connect to.
            **kwargs: Additional arguments (ignored for compatibility).

        Returns:
            Connected Sandbox instance.

        Raises:
            NotFoundException: If sandbox doesn't exist.
        """
        manager = get_sandbox_manager()
        info = manager.connect(sandbox_id)
        return cls(sandbox_id, info)

    @classmethod
    def list(cls, **kwargs) -> List[SandboxInfo]:
        """List all sandboxes.

        Returns:
            List of SandboxInfo objects.
        """
        manager = get_sandbox_manager()
        return manager.list()

    def kill(self, **kwargs) -> bool:
        """Kill this sandbox.

        Returns:
            True if killed successfully.
        """
        logger.info(f"Killing sandbox {self._sandbox_id}")
        return self._manager.kill(self._sandbox_id)

    def is_running(self, **kwargs) -> bool:
        """Check if sandbox is running.

        Returns:
            True if running.
        """
        return self._manager.is_running(self._sandbox_id)

    def set_timeout(self, timeout: int, **kwargs) -> None:
        """Update sandbox timeout.

        Args:
            timeout: New timeout in seconds.
        """
        self._manager.set_timeout(self._sandbox_id, timeout)

    def get_info(self, **kwargs) -> SandboxInfo:
        """Get sandbox information.

        Returns:
            SandboxInfo with current state.
        """
        info = self._manager.get_info(self._sandbox_id)
        if info is None:
            raise NotFoundException(f"Sandbox {self._sandbox_id} not found")
        self._info = info
        return info

    # Context manager support
    def __enter__(self) -> "Sandbox":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.kill()

    def __repr__(self) -> str:
        state = self._info.state.value if self._info else "unknown"
        return f"Sandbox(id={self._sandbox_id}, state={state})"
