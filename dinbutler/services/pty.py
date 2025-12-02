"""PTY (Pseudo-Terminal) support for interactive sessions."""

import logging
import socket
from typing import Optional, Dict, Iterator, Union, Any
from threading import Thread, Event
import struct

from dinbutler.services.docker_client import DockerClient, get_docker_client
from dinbutler.models.commands import PtySize, CommandHandle
from dinbutler.exceptions import SandboxException, NotFoundException

logger = logging.getLogger(__name__)


class PtyHandle:
    """Handle for PTY sessions with bidirectional I/O."""

    def __init__(
        self,
        exec_id: str,
        sandbox_id: str,
        docker_client: DockerClient,
        container_name: str,
        socket_conn: Any,
        pid: int = 0,
    ):
        self.exec_id = exec_id
        self.sandbox_id = sandbox_id
        self.pid = pid
        self._docker = docker_client
        self._container_name = container_name
        self._socket = socket_conn
        self._closed = Event()
        self._output_buffer: list = []
        self._read_thread: Optional[Thread] = None

    def _start_reading(self) -> None:
        """Background thread to read from PTY."""
        try:
            while not self._closed.is_set():
                # Docker multiplexes streams with 8-byte header
                # [stream_type(1), 0, 0, 0, size(4)]
                try:
                    # Try to read without header first (tty mode)
                    if hasattr(self._socket, '_sock'):
                        data = self._socket._sock.recv(4096)
                    else:
                        data = self._socket.recv(4096)

                    if not data:
                        break

                    self._output_buffer.append(data)
                except Exception as e:
                    if not self._closed.is_set():
                        logger.debug(f"PTY read error: {e}")
                    break
        finally:
            self._closed.set()

    def send_stdin(self, data: Union[str, bytes]) -> None:
        """Send data to PTY stdin."""
        if self._closed.is_set():
            raise SandboxException("PTY session closed", sandbox_id=self.sandbox_id)

        try:
            raw_data = data.encode() if isinstance(data, str) else data
            if hasattr(self._socket, '_sock'):
                self._socket._sock.send(raw_data)
            else:
                self._socket.send(raw_data)
        except Exception as e:
            raise SandboxException(f"Failed to send to PTY: {e}", sandbox_id=self.sandbox_id)

    def read(self, timeout: Optional[float] = None) -> bytes:
        """Read available output from PTY."""
        if self._output_buffer:
            return self._output_buffer.pop(0)
        return b""

    def read_all(self) -> bytes:
        """Read all buffered output."""
        output = b"".join(self._output_buffer)
        self._output_buffer.clear()
        return output

    def resize(self, size: PtySize) -> None:
        """Resize PTY terminal."""
        try:
            self._docker.exec_resize(self.exec_id, height=size.rows, width=size.cols)
        except Exception as e:
            raise SandboxException(f"Failed to resize PTY: {e}", sandbox_id=self.sandbox_id)

    def kill(self) -> bool:
        """Kill the PTY session."""
        self._closed.set()
        try:
            if self._socket:
                if hasattr(self._socket, '_sock'):
                    self._socket._sock.close()
                else:
                    self._socket.close()
            return True
        except Exception as e:
            logger.error(f"Failed to close PTY: {e}")
            return False

    def is_running(self) -> bool:
        """Check if PTY is still running."""
        if self._closed.is_set():
            return False
        try:
            info = self._docker.exec_inspect(self.exec_id)
            return info.get("Running", False)
        except Exception:
            return False

    def __iter__(self) -> Iterator[bytes]:
        """Iterate over PTY output."""
        while not self._closed.is_set() or self._output_buffer:
            if self._output_buffer:
                yield self._output_buffer.pop(0)
            else:
                import time
                time.sleep(0.01)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.kill()


class PtyService:
    """PTY service for interactive terminal sessions."""

    def __init__(self, docker_client: Optional[DockerClient] = None):
        self._docker = docker_client or get_docker_client()

    def _get_container_name(self, sandbox_id: str) -> str:
        """Get Docker container name for sandbox."""
        return f"e2b-{sandbox_id}"

    def create(
        self,
        sandbox_id: str,
        size: Optional[PtySize] = None,
        user: Optional[str] = None,
        cwd: Optional[str] = None,
        envs: Optional[Dict[str, str]] = None,
        shell: str = "/bin/bash",
        timeout: Optional[float] = 60,
        request_timeout: Optional[float] = None,
    ) -> PtyHandle:
        """Create a new PTY session.

        Args:
            sandbox_id: The sandbox ID.
            size: Terminal size (rows x cols).
            user: User to run as.
            cwd: Working directory.
            envs: Environment variables.
            shell: Shell to use.
            timeout: Session timeout.
            request_timeout: Request timeout.

        Returns:
            PtyHandle for the session.
        """
        container_name = self._get_container_name(sandbox_id)
        size = size or PtySize(rows=24, cols=80)

        try:
            # Build environment
            env = {
                "TERM": "xterm-256color",
                "COLUMNS": str(size.cols),
                "LINES": str(size.rows),
            }
            if envs:
                env.update(envs)

            # Create exec with TTY
            exec_id = self._docker.exec_create(
                container_name,
                shell,
                stdin=True,
                tty=True,
                environment=env,
                workdir=cwd,
                user=user,
            )

            # Start with socket for bidirectional I/O
            socket_conn = self._docker.exec_start(
                exec_id,
                socket=True,
                tty=True,
            )

            # Get PID
            info = self._docker.exec_inspect(exec_id)
            pid = info.get("Pid", 0)

            # Create handle
            handle = PtyHandle(
                exec_id=exec_id,
                sandbox_id=sandbox_id,
                docker_client=self._docker,
                container_name=container_name,
                socket_conn=socket_conn,
                pid=pid,
            )

            # Start reading thread
            thread = Thread(target=handle._start_reading, daemon=True)
            thread.start()
            handle._read_thread = thread

            return handle

        except Exception as e:
            raise SandboxException(f"Failed to create PTY: {e}", sandbox_id=sandbox_id)

    def resize(
        self,
        sandbox_id: str,
        pid: int,
        size: PtySize,
        request_timeout: Optional[float] = None,
    ) -> None:
        """Resize a PTY session.

        Note: This requires the exec_id, not pid. Use PtyHandle.resize() instead.
        """
        raise SandboxException(
            "Use PtyHandle.resize() to resize PTY sessions",
            sandbox_id=sandbox_id,
        )

    def send_stdin(
        self,
        sandbox_id: str,
        pid: int,
        data: bytes,
        request_timeout: Optional[float] = None,
    ) -> None:
        """Send data to PTY stdin.

        Note: Use PtyHandle.send_stdin() instead.
        """
        raise SandboxException(
            "Use PtyHandle.send_stdin() to send data to PTY",
            sandbox_id=sandbox_id,
        )

    def kill(
        self,
        sandbox_id: str,
        pid: int,
        request_timeout: Optional[float] = None,
    ) -> bool:
        """Kill a PTY session by PID.

        Args:
            sandbox_id: The sandbox ID.
            pid: Process ID of PTY.
            request_timeout: Request timeout.

        Returns:
            True if killed.
        """
        container_name = self._get_container_name(sandbox_id)

        try:
            result = self._docker.exec_run(
                container_name,
                f"kill -9 {pid}",
            )
            return result.exit_code == 0
        except Exception as e:
            logger.error(f"Failed to kill PTY {pid}: {e}")
            return False


# Global service instance
_pty_service: Optional[PtyService] = None


def get_pty_service() -> PtyService:
    """Get or create the global PTY service instance."""
    global _pty_service
    if _pty_service is None:
        _pty_service = PtyService()
    return _pty_service
