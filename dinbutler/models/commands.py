from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable, Any, Iterator, Union
from enum import Enum
import asyncio

@dataclass
class PtySize:
    rows: int = 24
    cols: int = 80

@dataclass
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int
    error: Optional[str] = None

@dataclass
class ProcessInfo:
    pid: int
    cmd: str
    args: List[str] = field(default_factory=list)
    envs: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    tag: Optional[str] = None

class CommandHandle:
    """Handle for background commands or PTY sessions."""

    def __init__(
        self,
        pid: int,
        exec_id: str,
        sandbox_id: str,
        _docker_client: Any = None,
    ):
        self.pid = pid
        self.exec_id = exec_id
        self.sandbox_id = sandbox_id
        self._docker = _docker_client
        self._on_stdout: Optional[Callable[[str], None]] = None
        self._on_stderr: Optional[Callable[[str], None]] = None

    def wait(
        self,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """Wait for command to complete and return result."""
        # Implementation will be added by commands service
        raise NotImplementedError("Use via sandbox.commands")

    def kill(self) -> bool:
        """Kill the running command."""
        raise NotImplementedError("Use via sandbox.commands")

    def disconnect(self) -> None:
        """Disconnect from command without killing it."""
        raise NotImplementedError("Use via sandbox.commands")

    def send_stdin(self, data: Union[str, bytes]) -> None:
        """Send data to command's stdin."""
        raise NotImplementedError("Use via sandbox.commands")

    def __iter__(self) -> Iterator[tuple]:
        """Iterate over command output."""
        raise NotImplementedError("Use via sandbox.commands")

# Type aliases
PtyOutput = bytes
Stdout = str
Stderr = str
