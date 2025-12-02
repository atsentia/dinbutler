"""
Security hooks for tool call validation and logging.

Implements pre-tool and post-tool hooks to enforce security policies:
- Path validation (prevent access outside allowed directories)
- Command blocking (prevent dangerous shell commands)
- Tool call logging (audit trail for all operations)
"""

import logging
import re
from pathlib import Path
from typing import Optional, Any

from .constants import (
    ALLOWED_PATHS,
    BLOCKED_COMMANDS,
    BLOCKED_COMMAND_PATTERNS,
    BLOCKED_PATHS,
    STRICT_PATH_VALIDATION,
    MAX_FILE_SIZE_MB,
)

logger = logging.getLogger(__name__)


class SecurityViolation(Exception):
    """Raised when a tool call violates security policies."""

    pass


class HookManager:
    """
    Manages security hooks for tool calls.

    Pre-tool hooks validate parameters before execution.
    Post-tool hooks log results after execution.
    """

    def __init__(self, sandbox_root: Path):
        """
        Initialize hook manager.

        Args:
            sandbox_root: Root directory for the sandbox
        """
        self.sandbox_root = sandbox_root.resolve()
        self._blocked_command_regex = self._compile_blocked_patterns()

    def _compile_blocked_patterns(self) -> list[re.Pattern]:
        """
        Compile regex patterns for blocked commands.

        Returns:
            List of compiled regex patterns
        """
        return [re.compile(pattern, re.IGNORECASE) for pattern in BLOCKED_COMMAND_PATTERNS]

    def pre_tool_hook(self, tool_name: str, parameters: dict) -> None:
        """
        Validate tool call before execution.

        Args:
            tool_name: Name of the tool being called
            parameters: Tool parameters

        Raises:
            SecurityViolation: If the tool call violates security policies
        """
        logger.debug(f"Pre-tool hook: {tool_name}")

        # Route to specific validators
        if tool_name in ["Read", "Write", "Edit"]:
            self._validate_file_access(tool_name, parameters)
        elif tool_name == "Bash":
            self._validate_bash_command(parameters)
        elif tool_name == "Glob":
            self._validate_glob_pattern(parameters)
        elif tool_name == "Grep":
            self._validate_grep_search(parameters)

    def post_tool_hook(
        self,
        tool_name: str,
        parameters: dict,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Log tool call result after execution.

        Args:
            tool_name: Name of the tool called
            parameters: Tool parameters
            result: Tool result (if successful)
            error: Error message (if failed)
        """
        if error:
            logger.warning(f"Tool {tool_name} failed: {error}")
        else:
            logger.debug(f"Tool {tool_name} succeeded")

    def _validate_file_access(self, tool_name: str, parameters: dict) -> None:
        """
        Validate file access operations.

        Args:
            tool_name: Tool name (Read/Write/Edit)
            parameters: Tool parameters

        Raises:
            SecurityViolation: If file access violates policies
        """
        file_path = parameters.get("file_path")
        if not file_path:
            return

        resolved_path = self._resolve_path(file_path)

        # Check for blocked paths (always enforced)
        if self._is_blocked_path(resolved_path):
            raise SecurityViolation(
                f"Access denied: {file_path} is in a blocked system directory"
            )

        # Check for allowed paths (if strict mode enabled)
        if STRICT_PATH_VALIDATION and not self._is_allowed_path(resolved_path):
            raise SecurityViolation(
                f"Access denied: {file_path} is outside allowed directories: {ALLOWED_PATHS}"
            )

        # Check file size for writes
        if tool_name in ["Write", "Edit"]:
            content = parameters.get("content", "") or parameters.get("new_string", "")
            if content:
                size_mb = len(content.encode("utf-8")) / (1024 * 1024)
                if size_mb > MAX_FILE_SIZE_MB:
                    raise SecurityViolation(
                        f"File too large: {size_mb:.2f}MB exceeds limit of {MAX_FILE_SIZE_MB}MB"
                    )

    def _validate_bash_command(self, parameters: dict) -> None:
        """
        Validate bash command execution.

        Args:
            parameters: Bash tool parameters

        Raises:
            SecurityViolation: If command is blocked
        """
        command = parameters.get("command", "")
        if not command:
            return

        # Check exact matches
        for blocked in BLOCKED_COMMANDS:
            if blocked in command:
                raise SecurityViolation(f"Blocked command detected: {blocked}")

        # Check regex patterns
        for pattern in self._blocked_command_regex:
            if pattern.search(command):
                raise SecurityViolation(
                    f"Command matches blocked pattern: {pattern.pattern}"
                )

        # Check for dangerous redirects
        if "> /dev/" in command or "| dd " in command:
            raise SecurityViolation("Dangerous redirect or pipe detected")

        # Check for attempts to escape sandbox
        if any(
            escape in command
            for escape in ["cd /", "cd ~", "cd $HOME", "../../../", "pushd /", "popd"]
        ):
            logger.warning(f"Potential sandbox escape attempt: {command}")

    def _validate_glob_pattern(self, parameters: dict) -> None:
        """
        Validate glob pattern search.

        Args:
            parameters: Glob tool parameters

        Raises:
            SecurityViolation: If pattern targets blocked paths
        """
        pattern = parameters.get("pattern", "")
        path = parameters.get("path")

        # If path specified, validate it
        if path:
            resolved_path = self._resolve_path(path)
            if self._is_blocked_path(resolved_path):
                raise SecurityViolation(f"Glob search blocked in: {path}")

    def _validate_grep_search(self, parameters: dict) -> None:
        """
        Validate grep search operation.

        Args:
            parameters: Grep tool parameters

        Raises:
            SecurityViolation: If search targets blocked paths
        """
        path = parameters.get("path")

        # If path specified, validate it
        if path:
            resolved_path = self._resolve_path(path)
            if self._is_blocked_path(resolved_path):
                raise SecurityViolation(f"Grep search blocked in: {path}")

    def _resolve_path(self, path_str: str) -> Path:
        """
        Resolve a path string to an absolute path within the sandbox.

        Args:
            path_str: Path string (absolute or relative)

        Returns:
            Resolved absolute path
        """
        path = Path(path_str)

        # If already absolute, resolve it
        if path.is_absolute():
            return path.resolve()

        # Otherwise, resolve relative to sandbox root
        return (self.sandbox_root / path).resolve()

    def _is_blocked_path(self, path: Path) -> bool:
        """
        Check if a path is in the blocked list.

        Args:
            path: Path to check

        Returns:
            True if path is blocked, False otherwise
        """
        path_str = str(path)

        # Check absolute blocked paths
        for blocked in BLOCKED_PATHS:
            # Expand home directory
            blocked_expanded = Path(blocked).expanduser().resolve()

            # Check if path is within blocked directory
            try:
                if blocked_expanded in path.parents or path == blocked_expanded:
                    return True
            except ValueError:
                # Different drives on Windows
                continue

            # Also check string prefix (for patterns like /etc/)
            if path_str.startswith(str(blocked_expanded)):
                return True

        return False

    def _is_allowed_path(self, path: Path) -> bool:
        """
        Check if a path is within allowed directories.

        Args:
            path: Path to check

        Returns:
            True if path is allowed, False otherwise
        """
        # Get relative path from sandbox root
        try:
            rel_path = path.relative_to(self.sandbox_root)
        except ValueError:
            # Path is outside sandbox root
            return False

        # Check if relative path starts with any allowed prefix
        rel_str = str(rel_path)
        for allowed in ALLOWED_PATHS:
            if rel_str.startswith(allowed) or rel_str == allowed.rstrip("/"):
                return True

        return False


class HookContext:
    """
    Context manager for executing tool calls with hooks.

    Usage:
        with HookContext(hook_manager, tool_name, parameters) as ctx:
            result = execute_tool(parameters)
            ctx.set_result(result)
    """

    def __init__(
        self,
        hook_manager: HookManager,
        tool_name: str,
        parameters: dict,
    ):
        """
        Initialize hook context.

        Args:
            hook_manager: Hook manager instance
            tool_name: Name of the tool
            parameters: Tool parameters
        """
        self.hook_manager = hook_manager
        self.tool_name = tool_name
        self.parameters = parameters
        self.result: Optional[str] = None
        self.error: Optional[str] = None

    def __enter__(self):
        """Enter context - run pre-tool hook."""
        self.hook_manager.pre_tool_hook(self.tool_name, self.parameters)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - run post-tool hook."""
        if exc_type is not None:
            self.error = str(exc_val)

        self.hook_manager.post_tool_hook(
            self.tool_name,
            self.parameters,
            result=self.result,
            error=self.error,
        )

        # Don't suppress exceptions
        return False

    def set_result(self, result: Any) -> None:
        """
        Set the tool call result.

        Args:
            result: Tool call result
        """
        self.result = str(result) if result is not None else None
