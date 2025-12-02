"""MCP Server for DinButler sandbox integration with Claude Code."""

import os
import subprocess
import json
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("DinButler Sandbox")


def run_sbx_cli(args: List[str]) -> str:
    """Execute sbx CLI command and return output.

    Args:
        args: List of command arguments to pass to sbx CLI

    Returns:
        Command output as string, or JSON error object if command failed
    """
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)  # Avoid uv conflicts

    result = subprocess.run(
        ["sbx"] + args,
        capture_output=True,
        text=True,
        env=env,
        cwd=os.getcwd()
    )

    if result.returncode != 0:
        return json.dumps({
            "error": result.stderr or "Command failed",
            "exit_code": result.returncode
        })
    return result.stdout


# ============================================================================
# Sandbox Lifecycle Management (7 tools)
# ============================================================================

@mcp.tool()
def init_sandbox(
    template: str = "default",
    timeout: int = 300,
    envs: Optional[str] = None
) -> str:
    """Initialize a new sandbox and save its ID locally.

    Creates a sandbox and stores the ID in .dinbutler/sandbox_id for use
    by subsequent commands without needing to specify the ID each time.

    Args:
        template: Template name (default, python, node) or Docker image
        timeout: Timeout in seconds (default 300)
        envs: Environment variables as JSON string, e.g. '{"KEY": "value"}'

    Returns:
        JSON with sandbox_id, template, timeout, and status
    """
    args = ["init", "--json", "--template", template, "--timeout", str(timeout)]

    # Parse and add environment variables
    if envs:
        try:
            env_dict = json.loads(envs)
            for key, value in env_dict.items():
                args.extend(["--envs", f"{key}={value}"])
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON for envs parameter"})

    return run_sbx_cli(args)


@mcp.tool()
def create_sandbox(
    template: str = "default",
    timeout: int = 3600,
    envs: Optional[str] = None
) -> str:
    """Create a new sandbox without local state tracking.

    Similar to init_sandbox but doesn't save the ID locally. Use this when
    you want to manage multiple sandboxes explicitly.

    Args:
        template: Template name (default, python, node) or Docker image
        timeout: Timeout in seconds (default 3600)
        envs: Environment variables as JSON string, e.g. '{"KEY": "value"}'

    Returns:
        JSON with sandbox_id, template, timeout, and envs
    """
    args = ["sandbox", "create", "--json", "--template", template, "--timeout", str(timeout)]

    if envs:
        try:
            env_dict = json.loads(envs)
            for key, value in env_dict.items():
                args.extend(["--envs", f"{key}={value}"])
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON for envs parameter"})

    return run_sbx_cli(args)


@mcp.tool()
def connect_sandbox(sandbox_id: Optional[str] = None) -> str:
    """Connect to an existing sandbox.

    If sandbox_id is not provided, uses the last active sandbox from local state.

    Args:
        sandbox_id: The sandbox ID to connect to (optional if using local state)

    Returns:
        Success message or error
    """
    args = ["sandbox", "connect"]
    if sandbox_id:
        args.append(sandbox_id)

    return run_sbx_cli(args)


@mcp.tool()
def kill_sandbox(sandbox_id: Optional[str] = None) -> str:
    """Kill a sandbox and stop its container.

    If sandbox_id is not provided, kills the last active sandbox from local state.

    Args:
        sandbox_id: The sandbox ID to kill (optional if using local state)

    Returns:
        Success message or error
    """
    args = ["sandbox", "kill"]
    if sandbox_id:
        args.append(sandbox_id)

    return run_sbx_cli(args)


@mcp.tool()
def get_sandbox_info(sandbox_id: Optional[str] = None) -> str:
    """Get detailed information about a sandbox.

    Retrieves sandbox metadata including template, state, environment variables,
    and start time.

    Args:
        sandbox_id: The sandbox ID (optional if using local state)

    Returns:
        JSON with sandbox_id, template_id, state, started_at, metadata, envs
    """
    args = ["sandbox", "info", "--json"]
    if sandbox_id:
        args.append(sandbox_id)

    return run_sbx_cli(args)


@mcp.tool()
def check_sandbox_status(sandbox_id: Optional[str] = None) -> str:
    """Check if a sandbox is currently running.

    Args:
        sandbox_id: The sandbox ID (optional if using local state)

    Returns:
        Status message indicating if sandbox is running
    """
    args = ["sandbox", "status"]
    if sandbox_id:
        args.append(sandbox_id)

    return run_sbx_cli(args)


@mcp.tool()
def list_sandboxes() -> str:
    """List all sandboxes on the system.

    Returns:
        JSON array of sandbox objects with sandbox_id, template_id, state, started_at
    """
    return run_sbx_cli(["sandbox", "list", "--json"])


# ============================================================================
# File Operations (10 tools)
# ============================================================================

@mcp.tool()
def list_files(
    sandbox_id: Optional[str] = None,
    path: str = "/",
    depth: int = 1
) -> str:
    """List directory contents in a sandbox.

    Args:
        sandbox_id: The sandbox ID (optional if using local state)
        path: Directory path to list (default: /)
        depth: How deep to recurse into subdirectories (default: 1)

    Returns:
        JSON array of file entries with name, path, type, size, mode, permissions
    """
    args = ["files", "ls", "--json", "--depth", str(depth)]
    if sandbox_id:
        args.append(sandbox_id)
    args.append(path)

    return run_sbx_cli(args)


@mcp.tool()
def read_file(
    sandbox_id: Optional[str] = None,
    path: str = ""
) -> str:
    """Read file contents from a sandbox.

    Args:
        sandbox_id: The sandbox ID (optional if using local state)
        path: File path to read (required)

    Returns:
        File contents as text, or error if file doesn't exist
    """
    if not path:
        return json.dumps({"error": "path parameter is required"})

    args = ["files", "read"]
    if sandbox_id:
        args.append(sandbox_id)
    args.append(path)

    return run_sbx_cli(args)


@mcp.tool()
def write_file(
    sandbox_id: Optional[str] = None,
    path: str = "",
    content: str = ""
) -> str:
    """Write content to a file in a sandbox.

    Creates parent directories if they don't exist. Overwrites existing files.

    Args:
        sandbox_id: The sandbox ID (optional if using local state)
        path: File path to write (required)
        content: Content to write to the file

    Returns:
        Success message with bytes written
    """
    if not path:
        return json.dumps({"error": "path parameter is required"})

    args = ["files", "write"]
    if sandbox_id:
        args.append(sandbox_id)
    args.extend([path, content])

    return run_sbx_cli(args)


@mcp.tool()
def file_exists(
    sandbox_id: Optional[str] = None,
    path: str = ""
) -> str:
    """Check if a file or directory exists in a sandbox.

    Args:
        sandbox_id: The sandbox ID (optional if using local state)
        path: Path to check (required)

    Returns:
        Success message if exists, error if not (exit code indicates result)
    """
    if not path:
        return json.dumps({"error": "path parameter is required"})

    args = ["files", "exists"]
    if sandbox_id:
        args.append(sandbox_id)
    args.append(path)

    return run_sbx_cli(args)


@mcp.tool()
def get_file_info(
    sandbox_id: Optional[str] = None,
    path: str = ""
) -> str:
    """Get detailed metadata about a file or directory.

    Args:
        sandbox_id: The sandbox ID (optional if using local state)
        path: Path to get info for (required)

    Returns:
        JSON with name, path, type, size, mode, permissions
    """
    if not path:
        return json.dumps({"error": "path parameter is required"})

    args = ["files", "info", "--json"]
    if sandbox_id:
        args.append(sandbox_id)
    args.append(path)

    return run_sbx_cli(args)


@mcp.tool()
def remove_file(
    sandbox_id: Optional[str] = None,
    path: str = ""
) -> str:
    """Remove a file or directory from a sandbox.

    Recursively removes directories and their contents.

    Args:
        sandbox_id: The sandbox ID (optional if using local state)
        path: Path to remove (required)

    Returns:
        Success message or error
    """
    if not path:
        return json.dumps({"error": "path parameter is required"})

    args = ["files", "remove"]
    if sandbox_id:
        args.append(sandbox_id)
    args.append(path)

    return run_sbx_cli(args)


@mcp.tool()
def create_directory(
    sandbox_id: Optional[str] = None,
    path: str = ""
) -> str:
    """Create a directory in a sandbox.

    Creates parent directories as needed.

    Args:
        sandbox_id: The sandbox ID (optional if using local state)
        path: Directory path to create (required)

    Returns:
        Success message or error
    """
    if not path:
        return json.dumps({"error": "path parameter is required"})

    args = ["files", "mkdir"]
    if sandbox_id:
        args.append(sandbox_id)
    args.append(path)

    return run_sbx_cli(args)


@mcp.tool()
def rename_file(
    sandbox_id: Optional[str] = None,
    old_path: str = "",
    new_path: str = ""
) -> str:
    """Rename or move a file/directory in a sandbox.

    Can be used to move files across directories within the same sandbox.

    Args:
        sandbox_id: The sandbox ID (optional if using local state)
        old_path: Current path (required)
        new_path: New path (required)

    Returns:
        Success message or error
    """
    if not old_path or not new_path:
        return json.dumps({"error": "old_path and new_path parameters are required"})

    args = ["files", "rename"]
    if sandbox_id:
        args.append(sandbox_id)
    args.extend([old_path, new_path])

    return run_sbx_cli(args)


@mcp.tool()
def upload_file(
    sandbox_id: Optional[str] = None,
    local_path: str = "",
    remote_path: str = ""
) -> str:
    """Upload a local file to a sandbox.

    Copies a file from the host machine into the sandbox container.

    Args:
        sandbox_id: The sandbox ID (optional if using local state)
        local_path: Path to local file on host machine (required)
        remote_path: Destination path in sandbox (required)

    Returns:
        Success message with bytes uploaded or error
    """
    if not local_path or not remote_path:
        return json.dumps({"error": "local_path and remote_path parameters are required"})

    args = ["files", "upload"]
    if sandbox_id:
        args.append(sandbox_id)
    args.extend([local_path, remote_path])

    return run_sbx_cli(args)


@mcp.tool()
def download_file(
    sandbox_id: Optional[str] = None,
    remote_path: str = "",
    local_path: str = ""
) -> str:
    """Download a file from a sandbox to the host machine.

    Copies a file from the sandbox container to the host machine.

    Args:
        sandbox_id: The sandbox ID (optional if using local state)
        remote_path: Path in sandbox (required)
        local_path: Destination path on host machine (required)

    Returns:
        Success message with bytes downloaded or error
    """
    if not remote_path or not local_path:
        return json.dumps({"error": "remote_path and local_path parameters are required"})

    args = ["files", "download"]
    if sandbox_id:
        args.append(sandbox_id)
    args.extend([remote_path, local_path])

    return run_sbx_cli(args)


# ============================================================================
# Command Execution (2 tools)
# ============================================================================

@mcp.tool()
def execute_command(
    sandbox_id: Optional[str] = None,
    command: str = "",
    cwd: Optional[str] = None,
    env_vars: Optional[str] = None,
    run_as_root: bool = False,
    timeout: int = 60,
    use_shell: bool = False
) -> str:
    """Execute a command in a sandbox.

    Runs a command synchronously and returns the result with stdout/stderr.

    Args:
        sandbox_id: The sandbox ID (optional if using local state)
        command: Command to execute (required)
        cwd: Working directory for command execution (optional)
        env_vars: Environment variables as JSON string, e.g. '{"KEY": "value"}' (optional)
        run_as_root: Run command as root user (default: false)
        timeout: Command timeout in seconds (default: 60)
        use_shell: Execute command in shell (default: false)

    Returns:
        JSON with status, sandbox_id, command, exit_code, stdout, stderr, error
    """
    if not command:
        return json.dumps({"error": "command parameter is required"})

    args = ["exec", "run", "--json", "--timeout", str(timeout)]

    if use_shell:
        args.append("--shell")

    if cwd:
        args.extend(["--cwd", cwd])

    if run_as_root:
        args.append("--root")

    # Parse and add environment variables
    if env_vars:
        try:
            env_dict = json.loads(env_vars)
            for key, value in env_dict.items():
                args.extend(["--env", f"{key}={value}"])
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON for env_vars parameter"})

    if sandbox_id:
        args.append(sandbox_id)

    args.append(command)

    return run_sbx_cli(args)


@mcp.tool()
def sandbox_fork(
    repo_url: str = "",
    branch: str = "main",
    prompt: str = "",
    num_forks: int = 1,
    model: str = "claude-sonnet-4"
) -> str:
    """Fork a repository and run AI-powered workflows in parallel sandboxes.

    This is a placeholder for future workflow integration. Currently not implemented
    in the CLI but reserved for orchestrating multiple AI agents in parallel sandboxes.

    Args:
        repo_url: Git repository URL to fork (required)
        branch: Git branch to checkout (default: main)
        prompt: Prompt to give to AI agent (required)
        num_forks: Number of parallel sandboxes to create (default: 1)
        model: AI model to use (default: claude-sonnet-4)

    Returns:
        JSON with fork results or error indicating feature not yet implemented
    """
    return json.dumps({
        "error": "sandbox_fork workflow not yet implemented",
        "status": "coming_soon",
        "message": "This feature will enable parallel AI agent workflows in future versions"
    })


# ============================================================================
# Server Entry Point
# ============================================================================

if __name__ == "__main__":
    mcp.run()
