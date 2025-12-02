"""Command execution operations for sandbox environments."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dinbutler.sandbox import Sandbox


@dataclass
class CommandResult:
    """Result of a command execution."""

    stdout: str
    stderr: str
    exit_code: int

    @property
    def output(self) -> str:
        """Combined stdout and stderr."""
        return self.stdout + self.stderr

    def __bool__(self) -> bool:
        """Return True if command succeeded (exit code 0)."""
        return self.exit_code == 0


class SandboxCommands:
    """Command execution for a sandbox container."""

    def __init__(self, sandbox: "Sandbox") -> None:
        self._sandbox = sandbox

    def run(
        self,
        command: str | list[str],
        *,
        cwd: str | None = None,
        envs: dict[str, str] | None = None,
        timeout: int | None = None,  # noqa: ARG002  # Reserved for E2B compatibility
        on_stdout: Callable[[str], None] | None = None,
        on_stderr: Callable[[str], None] | None = None,
    ) -> CommandResult:
        """Run a command in the sandbox.

        Args:
            command: Command to run (string or list of args)
            cwd: Working directory for the command
            envs: Environment variables to set
            timeout: Timeout in seconds (reserved for future use)
            on_stdout: Callback for stdout output
            on_stderr: Callback for stderr output

        Returns:
            CommandResult with stdout, stderr, and exit code
        """
        container = self._sandbox._get_container()
        if container is None:
            raise RuntimeError("Sandbox container is not running")

        cmd = ["/bin/sh", "-c", command] if isinstance(command, str) else list(command)

        # Build environment
        environment = envs or {}

        # Handle working directory by prepending cd
        if cwd and isinstance(command, str):
            cmd = ["/bin/sh", "-c", f"cd {cwd} && {command}"]
        elif cwd and isinstance(command, list):
            # For list commands, wrap in shell
            cmd = ["/bin/sh", "-c", f"cd {cwd} && {' '.join(command)}"]

        result = container.exec_run(
            cmd,
            environment=environment,
            demux=True,
        )

        stdout_bytes, stderr_bytes = result.output if isinstance(result.output, tuple) else (
            result.output,
            b"",
        )
        stdout = (stdout_bytes or b"").decode("utf-8")
        stderr = (stderr_bytes or b"").decode("utf-8")

        if on_stdout and stdout:
            on_stdout(stdout)
        if on_stderr and stderr:
            on_stderr(stderr)

        return CommandResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=result.exit_code,
        )
