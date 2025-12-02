"""Sandbox implementation using Docker for local code execution."""

from __future__ import annotations

import asyncio
import contextlib
import sys
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from dinbutler.commands import SandboxCommands
from dinbutler.execution import Execution, ExecutionError, Result
from dinbutler.files import SandboxFiles

if TYPE_CHECKING:
    import docker
    from docker.models.containers import Container


DEFAULT_IMAGE = "python:3.12-slim"


class Sandbox:
    """A local sandbox environment for executing code safely using Docker.

    This class provides an E2B-compatible API for running code in isolated
    Docker containers. It works with Docker or Colima on your local machine.

    Example:
        >>> from dinbutler import Sandbox
        >>> with Sandbox.create() as sandbox:
        ...     result = sandbox.run_code("print('Hello, World!')")
        ...     print(result.text)
        Hello, World!
    """

    def __init__(
        self,
        container: Container,
        client: docker.DockerClient,
        sandbox_id: str,
    ) -> None:
        """Initialize a Sandbox instance.

        Args:
            container: Docker container for this sandbox
            client: Docker client instance
            sandbox_id: Unique identifier for this sandbox
        """
        self._container = container
        self._client = client
        self._sandbox_id = sandbox_id
        self._files = SandboxFiles(self)
        self._commands = SandboxCommands(self)

    @classmethod
    def create(
        cls,
        *,
        template: str | None = None,
        timeout: int = 300,  # noqa: ARG003  # Reserved for E2B compatibility
        envs: dict[str, str] | None = None,
        cwd: str = "/home/user",
    ) -> Self:
        """Create a new sandbox instance.

        Args:
            template: Docker image to use (default: python:3.12-slim)
            timeout: Container lifetime in seconds (reserved for future use)
            envs: Environment variables to set in the container
            cwd: Working directory in the container

        Returns:
            A new Sandbox instance
        """
        import docker

        client = docker.from_env()
        image = template or DEFAULT_IMAGE
        sandbox_id = str(uuid.uuid4())[:8]

        # Ensure the image exists
        try:
            client.images.get(image)
        except docker.errors.ImageNotFound:
            client.images.pull(image)

        # Create and start the container
        environment = {"PYTHONUNBUFFERED": "1", **(envs or {})}

        container = client.containers.run(
            image,
            command="sleep infinity",
            detach=True,
            remove=True,
            name=f"dinbutler-{sandbox_id}",
            working_dir=cwd,
            environment=environment,
            mem_limit="512m",
            cpu_quota=50000,  # 50% of one CPU
            network_mode="bridge",
        )

        # Create the working directory
        container.exec_run(["mkdir", "-p", cwd])

        return cls(container=container, client=client, sandbox_id=sandbox_id)

    @property
    def sandbox_id(self) -> str:
        """Get the unique sandbox ID."""
        return self._sandbox_id

    @property
    def files(self) -> SandboxFiles:
        """Access file operations for this sandbox."""
        return self._files

    @property
    def commands(self) -> SandboxCommands:
        """Access command execution for this sandbox."""
        return self._commands

    def _get_container(self) -> Container | None:
        """Get the underlying Docker container."""
        return self._container

    def run_code(
        self,
        code: str,
        *,
        language: str = "python",
        on_stdout: Callable[[str], None] | None = None,
        on_stderr: Callable[[str], None] | None = None,
        envs: dict[str, str] | None = None,
        timeout: int | None = None,  # noqa: ARG002  # Reserved for E2B compatibility
        cwd: str | None = None,
    ) -> Execution:
        """Execute code in the sandbox.

        Args:
            code: The code to execute
            language: Programming language (python, javascript, bash, etc.)
            on_stdout: Callback for stdout output
            on_stderr: Callback for stderr output
            envs: Additional environment variables
            timeout: Execution timeout in seconds (reserved for future use)
            cwd: Working directory for execution

        Returns:
            Execution result containing output and any errors
        """
        container = self._get_container()
        if container is None:
            raise RuntimeError("Sandbox container is not running")

        # Determine the command based on language
        if language == "python":
            cmd = ["python3", "-c", code]
        elif language in ("javascript", "js"):
            cmd = ["node", "-e", code]
        elif language == "bash":
            cmd = ["/bin/bash", "-c", code]
        elif language == "sh":
            cmd = ["/bin/sh", "-c", code]
        else:
            # Default to shell execution
            cmd = ["/bin/sh", "-c", code]

        environment = envs or {}
        work_dir = cwd

        result = container.exec_run(
            cmd,
            environment=environment,
            workdir=work_dir,
            demux=True,
        )

        # Handle the output
        stdout_bytes: bytes
        stderr_bytes: bytes

        if isinstance(result.output, tuple):
            stdout_bytes, stderr_bytes = result.output
            stdout_bytes = stdout_bytes or b""
            stderr_bytes = stderr_bytes or b""
        else:
            stdout_bytes = result.output or b""
            stderr_bytes = b""

        stdout = stdout_bytes.decode("utf-8")
        stderr = stderr_bytes.decode("utf-8")

        if on_stdout and stdout:
            on_stdout(stdout)
        if on_stderr and stderr:
            on_stderr(stderr)

        # Build execution result
        execution = Execution(
            results=[Result(text=stdout.strip())] if stdout.strip() else [],
            logs=stdout.splitlines(),
            exit_code=result.exit_code,
        )

        # Check for errors
        if result.exit_code != 0:
            execution.error = ExecutionError(
                name="ExecutionError",
                value=f"Command exited with code {result.exit_code}",
                traceback=stderr,
            )

        return execution

    def close(self) -> None:
        """Stop and remove the sandbox container."""
        if self._container:
            with contextlib.suppress(Exception):
                self._container.stop(timeout=1)
            self._container = None  # noqa: FBT003

    def __enter__(self) -> Self:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit context manager and cleanup."""
        self.close()


class AsyncSandbox:
    """Async version of the Sandbox class.

    Provides the same API as Sandbox but with async/await support.

    Example:
        >>> from dinbutler import AsyncSandbox
        >>> async with await AsyncSandbox.create() as sandbox:
        ...     result = await sandbox.run_code("print('Hello, async!')")
        ...     print(result.text)
    """

    def __init__(self, sandbox: Sandbox) -> None:
        """Initialize AsyncSandbox wrapper.

        Args:
            sandbox: The underlying synchronous Sandbox instance
        """
        self._sandbox = sandbox

    @classmethod
    async def create(
        cls,
        *,
        template: str | None = None,
        timeout: int = 300,
        envs: dict[str, str] | None = None,
        cwd: str = "/home/user",
    ) -> Self:
        """Create a new async sandbox instance.

        Args:
            template: Docker image to use
            timeout: Container timeout in seconds
            envs: Environment variables
            cwd: Working directory

        Returns:
            A new AsyncSandbox instance
        """
        sandbox = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Sandbox.create(
                template=template,
                timeout=timeout,
                envs=envs,
                cwd=cwd,
            ),
        )
        return cls(sandbox)

    @property
    def sandbox_id(self) -> str:
        """Get the unique sandbox ID."""
        return self._sandbox.sandbox_id

    @property
    def files(self) -> SandboxFiles:
        """Access file operations for this sandbox."""
        return self._sandbox.files

    @property
    def commands(self) -> SandboxCommands:
        """Access command execution for this sandbox."""
        return self._sandbox.commands

    async def run_code(
        self,
        code: str,
        *,
        language: str = "python",
        on_stdout: Callable[[str], None] | None = None,
        on_stderr: Callable[[str], None] | None = None,
        envs: dict[str, str] | None = None,
        timeout: int | None = None,
        cwd: str | None = None,
    ) -> Execution:
        """Execute code in the sandbox asynchronously.

        Args:
            code: The code to execute
            language: Programming language
            on_stdout: Callback for stdout
            on_stderr: Callback for stderr
            envs: Environment variables
            timeout: Execution timeout
            cwd: Working directory

        Returns:
            Execution result
        """
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._sandbox.run_code(
                code,
                language=language,
                on_stdout=on_stdout,
                on_stderr=on_stderr,
                envs=envs,
                timeout=timeout,
                cwd=cwd,
            ),
        )

    async def close(self) -> None:
        """Stop and remove the sandbox container."""
        await asyncio.get_event_loop().run_in_executor(None, self._sandbox.close)

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager and cleanup."""
        await self.close()
