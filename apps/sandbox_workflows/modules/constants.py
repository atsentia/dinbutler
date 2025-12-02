"""
Configuration constants for sandbox workflows.

This module defines limits, security policies, and default values
for the workflow engine.
"""

from pathlib import Path

# Fork configuration
MAX_FORKS = 100
"""Maximum number of parallel forks allowed."""

DEFAULT_FORKS = 1
"""Default number of forks if not specified."""

MAX_AGENT_TURNS = 100
"""Maximum number of turns an agent can take in a single fork."""

# Model configuration
DEFAULT_MODEL = "sonnet"
"""Default Claude model to use."""

MODEL_IDENTIFIERS = {
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-20250514",
    "haiku": "claude-3-5-haiku-20241022",
}
"""Mapping of short model names to full identifiers."""

# Security policies
ALLOWED_PATHS = [
    "temp/",
    "specs/",
    "workspace/",
    "src/",
    "tests/",
    "docs/",
    "scripts/",
    "config/",
    "data/",
]
"""
List of directory prefixes that agents are allowed to access.

Agents can only read/write files within these directories relative
to the sandbox root. Attempts to access paths outside these directories
will be blocked by the security hooks.
"""

BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf /*",
    "sudo rm",
    "mkfs",
    "dd if=",
    ":(){ :|:& };:",  # Fork bomb
    "chmod 000",
    "chown root",
    "mkfs.ext4",
    "fdisk",
    "parted",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
]
"""
List of dangerous shell commands that are explicitly blocked.

These commands can cause system damage, data loss, or denial of service.
The hook manager will reject any tool call attempting to execute these.
"""

BLOCKED_COMMAND_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"sudo\s+rm",
    r"mkfs",
    r"dd\s+if=",
    r"chmod\s+000",
    r"shutdown",
    r"reboot",
    r"halt",
    r"poweroff",
]
"""
Regex patterns for dangerous commands.

Used by the hook manager for pattern-based command blocking.
"""

# Logging configuration
DEFAULT_LOG_DIR = Path("./logs")
"""Default directory for fork logs."""

LOG_FORMAT = "%(asctime)s - Fork %(fork_id)s - %(levelname)s - %(message)s"
"""Log message format for fork loggers."""

LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
"""Timestamp format for log messages."""

# Resource limits
MAX_FILE_SIZE_MB = 100
"""Maximum file size (in MB) that agents can read/write."""

MAX_EXECUTION_TIME_SECONDS = 3600
"""Maximum execution time (in seconds) for a single fork."""

MAX_MEMORY_MB = 2048
"""Maximum memory (in MB) that a fork can consume."""

# Tool call limits
MAX_TOOL_CALLS_PER_TURN = 50
"""Maximum number of tool calls allowed in a single agent turn."""

MAX_BASH_EXECUTION_TIME_MS = 120000
"""Maximum execution time (in milliseconds) for a single bash command."""

# Git configuration
GIT_CLONE_DEPTH = 1
"""Depth for shallow git clones (reduce disk usage)."""

GIT_TIMEOUT_SECONDS = 300
"""Timeout for git operations (clone, fetch, etc.)."""

# Agent behavior
AGENT_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.md"
"""Path to the agent system prompt template."""

AGENT_MAX_RETRIES = 3
"""Maximum number of retries for failed tool calls."""

AGENT_RETRY_DELAY_SECONDS = 2
"""Delay (in seconds) between tool call retries."""

# Sandbox configuration
SANDBOX_TEMP_PREFIX = "obox_sandbox_"
"""Prefix for temporary sandbox directories."""

SANDBOX_CLEANUP_ON_ERROR = False
"""Whether to clean up sandbox directories on error (useful for debugging)."""

SANDBOX_CLEANUP_ON_SUCCESS = False
"""Whether to clean up sandbox directories on success (preserve results by default)."""

# Performance tuning
THREAD_POOL_MAX_WORKERS = 10
"""Maximum number of worker threads for parallel fork execution."""

ENABLE_TOOL_CALL_CACHE = True
"""Enable caching of tool call results to reduce redundant operations."""

# Validation settings
STRICT_PATH_VALIDATION = True
"""
Enable strict path validation.

When True, agents cannot access any paths outside ALLOWED_PATHS.
When False, only BLOCKED_PATHS are restricted (more permissive).
"""

BLOCKED_PATHS = [
    "/etc/",
    "/var/",
    "/usr/",
    "/bin/",
    "/sbin/",
    "/boot/",
    "/sys/",
    "/proc/",
    "~/.ssh/",
    "~/.aws/",
    "~/.config/",
]
"""
Paths that are always blocked, regardless of STRICT_PATH_VALIDATION setting.

These are system-critical or sensitive user directories.
"""
