"""Exception classes for Colima E2B.

These exceptions mirror E2B's exception hierarchy for API compatibility.
"""

from typing import Optional
from dataclasses import dataclass


class SandboxException(Exception):
    """Base exception for sandbox operations."""

    def __init__(self, message: str, sandbox_id: Optional[str] = None):
        self.message = message
        self.sandbox_id = sandbox_id
        super().__init__(message)


class TimeoutException(SandboxException):
    """Raised when an operation times out."""

    def __init__(
        self,
        message: str = "Operation timed out",
        sandbox_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.timeout = timeout
        super().__init__(message, sandbox_id)


class NotFoundException(SandboxException):
    """Raised when a resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        sandbox_id: Optional[str] = None,
        resource_type: Optional[str] = None,
    ):
        self.resource_type = resource_type
        super().__init__(message, sandbox_id)


class InvalidArgumentException(SandboxException):
    """Raised when invalid arguments are provided."""

    def __init__(
        self,
        message: str = "Invalid argument",
        argument_name: Optional[str] = None,
        sandbox_id: Optional[str] = None,
    ):
        self.argument_name = argument_name
        super().__init__(message, sandbox_id)


class NotEnoughSpaceException(SandboxException):
    """Raised when there's insufficient disk space."""
    pass


class AuthenticationException(Exception):
    """Raised for authentication failures.

    Note: Not a SandboxException since it's not sandbox-specific.
    """
    pass


class RateLimitException(SandboxException):
    """Raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None,
        sandbox_id: Optional[str] = None,
    ):
        self.retry_after = retry_after
        super().__init__(message, sandbox_id)


@dataclass
class CommandExitException(SandboxException):
    """Raised when a command exits with non-zero code.

    Contains the command result for inspection.
    """

    stdout: str
    stderr: str
    exit_code: int
    error: Optional[str] = None

    def __init__(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        error: Optional[str] = None,
        sandbox_id: Optional[str] = None,
    ):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.error = error
        message = f"Command exited with code {exit_code}"
        if stderr:
            message += f": {stderr[:200]}"
        super().__init__(message, sandbox_id)


class TemplateException(SandboxException):
    """Raised for template-related errors."""

    def __init__(
        self,
        message: str = "Template error",
        template_name: Optional[str] = None,
        sandbox_id: Optional[str] = None,
    ):
        self.template_name = template_name
        super().__init__(message, sandbox_id)


class BuildException(Exception):
    """Raised during template building."""

    def __init__(self, message: str, build_id: Optional[str] = None):
        self.build_id = build_id
        super().__init__(message)


class FileUploadException(BuildException):
    """Raised during file upload operations."""

    def __init__(
        self,
        message: str = "File upload failed",
        file_path: Optional[str] = None,
        build_id: Optional[str] = None,
    ):
        self.file_path = file_path
        super().__init__(message, build_id)


class DockerException(SandboxException):
    """Raised for Docker-specific errors."""

    def __init__(
        self,
        message: str,
        docker_error: Optional[str] = None,
        sandbox_id: Optional[str] = None,
    ):
        self.docker_error = docker_error
        super().__init__(message, sandbox_id)


class ColimaException(SandboxException):
    """Raised for Colima-specific errors."""

    def __init__(
        self,
        message: str = "Colima error",
        suggestion: Optional[str] = None,
    ):
        self.suggestion = suggestion
        full_message = message
        if suggestion:
            full_message += f"\nSuggestion: {suggestion}"
        super().__init__(full_message)


# Helper functions for creating common exceptions

def format_request_timeout_error(
    operation: str = "request",
    timeout: Optional[float] = None,
) -> TimeoutException:
    """Create a formatted timeout exception for requests."""
    msg = f"The {operation} timed out"
    if timeout:
        msg += f" after {timeout}s"
    return TimeoutException(msg, timeout=timeout)


def format_sandbox_timeout_exception(
    sandbox_id: str,
    timeout: float,
) -> TimeoutException:
    """Create a formatted timeout exception for sandbox operations."""
    return TimeoutException(
        f"Sandbox {sandbox_id} timed out after {timeout}s",
        sandbox_id=sandbox_id,
        timeout=timeout,
    )


def format_execution_timeout_error(
    command: str,
    timeout: float,
    sandbox_id: Optional[str] = None,
) -> TimeoutException:
    """Create a formatted timeout exception for command execution."""
    cmd_preview = command[:50] + "..." if len(command) > 50 else command
    return TimeoutException(
        f"Command '{cmd_preview}' timed out after {timeout}s",
        sandbox_id=sandbox_id,
        timeout=timeout,
    )


def format_not_found_error(
    resource_type: str,
    resource_id: str,
    sandbox_id: Optional[str] = None,
) -> NotFoundException:
    """Create a formatted not found exception."""
    return NotFoundException(
        f"{resource_type} '{resource_id}' not found",
        sandbox_id=sandbox_id,
        resource_type=resource_type,
    )
