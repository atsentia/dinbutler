"""Command execution inside sandbox containers."""

import logging
import time
from typing import Optional, Dict, List, Callable, Union, Iterator, Any
from threading import Thread, Event
import re

from dinbutler.services.docker_client import DockerClient, get_docker_client
from dinbutler.models.commands import (
    CommandResult,
    CommandHandle,
    ProcessInfo,
)
from dinbutler.exceptions import (
    SandboxException,
    NotFoundException,
    TimeoutException,
    CommandExitException,
    format_execution_timeout_error,
)

logger = logging.getLogger(__name__)


class LiveCommandHandle(CommandHandle):
    """Handle for background commands with live output streaming."""

    def __init__(
        self,
        pid: int,
        exec_id: str,
        sandbox_id: str,
        docker_client: DockerClient,
        container_name: str,
    ):
        super().__init__(pid, exec_id, sandbox_id, docker_client)
        self._container_name = container_name
        self._stdout_buffer: List[str] = []
        self._stderr_buffer: List[str] = []
        self._exit_code: Optional[int] = None
        self._finished = Event()
        self._stream_thread: Optional[Thread] = None

    def _start_streaming(self, stream: Iterator[bytes]) -> None:
        """Stream output in background thread."""
        try:
            for chunk in stream:
                if self._finished.is_set():
                    break
                decoded = chunk.decode("utf-8", errors="replace")
                self._stdout_buffer.append(decoded)
                if self._on_stdout:
                    self._on_stdout(decoded)
        except Exception as e:
            logger.debug(f"Stream ended: {e}")
        finally:
            self._finished.set()
            # Get exit code
            try:
                info = self._docker.exec_inspect(self.exec_id)
                self._exit_code = info.get("ExitCode", -1)
            except Exception:
                self._exit_code = -1

    def wait(
        self,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
        timeout: Optional[float] = None,
    ) -> CommandResult:
        """Wait for command to complete."""
        self._on_stdout = on_stdout
        self._on_stderr = on_stderr

        start_time = time.time()
        while not self._finished.is_set():
            if timeout and (time.time() - start_time) > timeout:
                self.kill()
                raise format_execution_timeout_error(
                    "command", timeout, self.sandbox_id
                )
            time.sleep(0.1)

        return CommandResult(
            stdout="".join(self._stdout_buffer),
            stderr="".join(self._stderr_buffer),
            exit_code=self._exit_code if self._exit_code is not None else -1,
        )

    def kill(self) -> bool:
        """Kill the running command."""
        try:
            # Kill process by PID
            self._docker.exec_run(
                self._container_name,
                f"kill -9 {self.pid}",
            )
            self._finished.set()
            return True
        except Exception as e:
            logger.error(f"Failed to kill process: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect without killing."""
        self._finished.set()

    def send_stdin(self, data: Union[str, bytes]) -> None:
        """Send data to stdin (not supported for exec)."""
        raise SandboxException("stdin not supported for background commands")

    def __iter__(self) -> Iterator[tuple]:
        """Iterate over output."""
        while not self._finished.is_set() or self._stdout_buffer:
            if self._stdout_buffer:
                yield (self._stdout_buffer.pop(0), None, None)
            else:
                time.sleep(0.01)


class CommandsService:
    """Execute commands inside sandbox containers."""

    def __init__(self, docker_client: Optional[DockerClient] = None):
        self._docker = docker_client or get_docker_client()

    def _get_container_name(self, sandbox_id: str) -> str:
        """Get Docker container name for sandbox."""
        return f"e2b-{sandbox_id}"

    def run(
        self,
        sandbox_id: str,
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
        """Run a command in the sandbox.

        Args:
            sandbox_id: The sandbox ID.
            cmd: Command to execute.
            background: Run in background (returns handle instead of result).
            envs: Environment variables.
            cwd: Working directory.
            user: User to run as.
            on_stdout: Callback for stdout lines.
            on_stderr: Callback for stderr lines.
            timeout: Timeout in seconds (foreground only).
            request_timeout: Request timeout.

        Returns:
            CommandResult for foreground, CommandHandle for background.

        Raises:
            CommandExitException: If command exits with non-zero code.
            TimeoutException: If command times out.
        """
        container_name = self._get_container_name(sandbox_id)

        if background:
            return self._run_background(
                container_name, sandbox_id, cmd, envs, cwd, user, on_stdout, on_stderr
            )
        else:
            return self._run_foreground(
                container_name, sandbox_id, cmd, envs, cwd, user,
                on_stdout, on_stderr, timeout
            )

    def _run_foreground(
        self,
        container_name: str,
        sandbox_id: str,
        cmd: str,
        envs: Optional[Dict[str, str]],
        cwd: Optional[str],
        user: Optional[str],
        on_stdout: Optional[Callable[[str], None]],
        on_stderr: Optional[Callable[[str], None]],
        timeout: float,
    ) -> CommandResult:
        """Run command and wait for completion."""
        try:
            # Wrap command with timeout
            wrapped_cmd = f"timeout {timeout} sh -c '{cmd}'"

            result = self._docker.exec_run(
                container_name,
                cmd,
                environment=envs,
                workdir=cwd,
                user=user,
                demux=True,
            )

            stdout = ""
            stderr = ""

            if result.output:
                if result.output[0]:
                    stdout = result.output[0].decode("utf-8", errors="replace")
                    if on_stdout:
                        for line in stdout.split("\n"):
                            on_stdout(line)
                if result.output[1]:
                    stderr = result.output[1].decode("utf-8", errors="replace")
                    if on_stderr:
                        for line in stderr.split("\n"):
                            on_stderr(line)

            exit_code = result.exit_code

            # Check for timeout (exit code 124)
            if exit_code == 124:
                raise format_execution_timeout_error(cmd, timeout, sandbox_id)

            return CommandResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
            )

        except TimeoutException:
            raise
        except Exception as e:
            raise SandboxException(f"Failed to execute command: {e}", sandbox_id=sandbox_id)

    def _run_background(
        self,
        container_name: str,
        sandbox_id: str,
        cmd: str,
        envs: Optional[Dict[str, str]],
        cwd: Optional[str],
        user: Optional[str],
        on_stdout: Optional[Callable[[str], None]],
        on_stderr: Optional[Callable[[str], None]],
    ) -> LiveCommandHandle:
        """Run command in background, return handle."""
        try:
            # Create exec instance
            exec_id = self._docker.exec_create(
                container_name,
                cmd,
                stdin=False,
                tty=False,
                environment=envs,
                workdir=cwd,
                user=user,
            )

            # Start exec with streaming
            stream = self._docker.exec_start(exec_id, stream=True, detach=False)

            # Get PID (inspect exec)
            info = self._docker.exec_inspect(exec_id)
            pid = info.get("Pid", 0)

            # Create handle
            handle = LiveCommandHandle(
                pid=pid,
                exec_id=exec_id,
                sandbox_id=sandbox_id,
                docker_client=self._docker,
                container_name=container_name,
            )
            handle._on_stdout = on_stdout
            handle._on_stderr = on_stderr

            # Start streaming thread
            thread = Thread(target=handle._start_streaming, args=(stream,), daemon=True)
            thread.start()
            handle._stream_thread = thread

            return handle

        except Exception as e:
            raise SandboxException(f"Failed to start background command: {e}", sandbox_id=sandbox_id)

    def list(
        self,
        sandbox_id: str,
        request_timeout: Optional[float] = None,
    ) -> List[ProcessInfo]:
        """List running processes in sandbox.

        Args:
            sandbox_id: The sandbox ID.
            request_timeout: Request timeout.

        Returns:
            List of ProcessInfo objects.
        """
        container_name = self._get_container_name(sandbox_id)

        try:
            result = self._docker.exec_run(
                container_name,
                "ps aux --no-headers",
                demux=True,
            )

            stdout = result.output[0].decode() if result.output[0] else ""
            processes = []

            for line in stdout.strip().split("\n"):
                if not line.strip():
                    continue

                # Parse ps aux output
                # USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    user = parts[0]
                    pid = int(parts[1])
                    cmd_full = parts[10]

                    # Split command and args
                    cmd_parts = cmd_full.split()
                    cmd = cmd_parts[0] if cmd_parts else ""
                    args = cmd_parts[1:] if len(cmd_parts) > 1 else []

                    processes.append(ProcessInfo(
                        pid=pid,
                        cmd=cmd,
                        args=args,
                    ))

            return processes

        except Exception as e:
            raise SandboxException(f"Failed to list processes: {e}", sandbox_id=sandbox_id)

    def kill(
        self,
        sandbox_id: str,
        pid: int,
        signal: str = "KILL",
        request_timeout: Optional[float] = None,
    ) -> bool:
        """Kill a process by PID.

        Args:
            sandbox_id: The sandbox ID.
            pid: Process ID to kill.
            signal: Signal to send (default KILL).
            request_timeout: Request timeout.

        Returns:
            True if killed successfully.
        """
        container_name = self._get_container_name(sandbox_id)

        try:
            result = self._docker.exec_run(
                container_name,
                f"kill -{signal} {pid}",
            )
            return result.exit_code == 0
        except Exception as e:
            logger.error(f"Failed to kill process {pid}: {e}")
            return False

    def send_stdin(
        self,
        sandbox_id: str,
        pid: int,
        data: str,
        request_timeout: Optional[float] = None,
    ) -> None:
        """Send data to process stdin.

        Note: This is limited in Docker exec. For full stdin support,
        use PTY sessions.
        """
        raise SandboxException(
            "Direct stdin to PID not supported. Use PTY sessions for interactive input.",
            sandbox_id=sandbox_id,
        )

    def connect(
        self,
        sandbox_id: str,
        pid: int,
        timeout: Optional[float] = 60,
        request_timeout: Optional[float] = None,
    ) -> CommandHandle:
        """Connect to a running process.

        Note: Limited support in Docker. Can only track process existence.
        """
        container_name = self._get_container_name(sandbox_id)

        # Check if process exists
        result = self._docker.exec_run(
            container_name,
            f"kill -0 {pid}",
        )

        if result.exit_code != 0:
            raise NotFoundException(f"Process {pid} not found", sandbox_id=sandbox_id)

        # Return a handle that can check process status
        return LiveCommandHandle(
            pid=pid,
            exec_id="",
            sandbox_id=sandbox_id,
            docker_client=self._docker,
            container_name=container_name,
        )


# Global service instance
_commands_service: Optional[CommandsService] = None


def get_commands_service() -> CommandsService:
    """Get or create the global commands service instance."""
    global _commands_service
    if _commands_service is None:
        _commands_service = CommandsService()
    return _commands_service
