"""Sandbox lifecycle management commands."""

import click
from dinbutler import Sandbox
from apps.sandbox_cli.modules.state import save_sandbox_id, get_sandbox_id_or_arg
from apps.sandbox_cli.modules.output import (
    output_json,
    output_text,
    output_error,
    output_success,
    output_table,
)


@click.group()
def sandbox():
    """Manage sandbox lifecycle (create, connect, kill, etc.)."""
    pass


@sandbox.command()
@click.option("--template", default="default", help="Template to use for sandbox")
@click.option("--timeout", type=int, default=3600, help="Timeout in seconds")
@click.option(
    "--envs",
    multiple=True,
    help="Environment variables in KEY=VALUE format (can be used multiple times)",
)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def create(template, timeout, envs, json_output):
    """Create a new sandbox.

    Examples:
        sandbox create
        sandbox create --template python
        sandbox create --timeout 7200 --envs API_KEY=xxx --envs DEBUG=true
        sandbox create --json
    """
    try:
        # Parse environment variables
        env_dict = {}
        for env in envs:
            if "=" not in env:
                output_error(f"Invalid environment variable format: {env} (expected KEY=VALUE)")
                return
            key, value = env.split("=", 1)
            env_dict[key] = value

        # Create sandbox
        sb = Sandbox.create(template=template, timeout=timeout, envs=env_dict)

        # Save sandbox ID to state
        save_sandbox_id(sb.sandbox_id)

        if json_output:
            output_json({
                "sandbox_id": sb.sandbox_id,
                "template": template,
                "timeout": timeout,
                "envs": env_dict,
            })
        else:
            output_success(f"Created sandbox: {sb.sandbox_id}")
            if env_dict:
                output_text(f"Environment variables: {', '.join(env_dict.keys())}")
    except Exception as e:
        output_error(f"Failed to create sandbox: {str(e)}")


@sandbox.command()
@click.argument("sandbox_id", required=False)
def connect(sandbox_id):
    """Connect to an existing sandbox.

    Examples:
        sandbox connect sb_123abc
        sandbox connect  # Uses last active sandbox
    """
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        if not sandbox_id:
            output_error("No sandbox ID provided and no active sandbox found")
            return

        sb = Sandbox.connect(sandbox_id)

        # Save sandbox ID to state
        save_sandbox_id(sb.sandbox_id)

        output_success(f"Connected to sandbox: {sb.sandbox_id}")
    except Exception as e:
        output_error(f"Failed to connect to sandbox: {str(e)}")


@sandbox.command()
@click.argument("sandbox_id", required=False)
def kill(sandbox_id):
    """Kill a sandbox.

    Examples:
        sandbox kill sb_123abc
        sandbox kill  # Kills last active sandbox
    """
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        if not sandbox_id:
            output_error("No sandbox ID provided and no active sandbox found")
            return

        sb = Sandbox.connect(sandbox_id)
        success = sb.kill()

        if success:
            output_success(f"Killed sandbox: {sandbox_id}")
        else:
            output_error(f"Failed to kill sandbox: {sandbox_id}")
    except Exception as e:
        output_error(f"Failed to kill sandbox: {str(e)}")


@sandbox.command()
@click.argument("sandbox_id", required=False)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def info(sandbox_id, json_output):
    """Get detailed information about a sandbox.

    Examples:
        sandbox info sb_123abc
        sandbox info --json
        sandbox info  # Uses last active sandbox
    """
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        if not sandbox_id:
            output_error("No sandbox ID provided and no active sandbox found")
            return

        sb = Sandbox.connect(sandbox_id)
        sandbox_info = sb.get_info()

        if json_output:
            output_json({
                "sandbox_id": sandbox_info.sandbox_id,
                "template_id": sandbox_info.template_id,
                "state": sandbox_info.state,
                "started_at": sandbox_info.started_at,
                "metadata": sandbox_info.metadata,
                "envs": sandbox_info.envs,
            })
        else:
            output_text(f"Sandbox ID: {sandbox_info.sandbox_id}")
            output_text(f"Template: {sandbox_info.template_id}")
            output_text(f"State: {sandbox_info.state}")
            output_text(f"Started: {sandbox_info.started_at}")

            if sandbox_info.metadata:
                output_text(f"Metadata: {sandbox_info.metadata}")

            if sandbox_info.envs:
                output_text("Environment variables:")
                for key, value in sandbox_info.envs.items():
                    output_text(f"  {key}={value}")
    except Exception as e:
        output_error(f"Failed to get sandbox info: {str(e)}")


@sandbox.command()
@click.argument("sandbox_id", required=False)
def status(sandbox_id):
    """Check if a sandbox is running.

    Examples:
        sandbox status sb_123abc
        sandbox status  # Checks last active sandbox
    """
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        if not sandbox_id:
            output_error("No sandbox ID provided and no active sandbox found")
            return

        sb = Sandbox.connect(sandbox_id)
        is_running = sb.is_running()

        if is_running:
            output_success(f"Sandbox {sandbox_id} is running")
        else:
            output_text(f"Sandbox {sandbox_id} is not running")
    except Exception as e:
        output_error(f"Failed to check sandbox status: {str(e)}")


@sandbox.command()
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def list(json_output):
    """List all sandboxes.

    Examples:
        sandbox list
        sandbox list --json
    """
    try:
        sandboxes = Sandbox.list()

        if json_output:
            output_json([
                {
                    "sandbox_id": sb.sandbox_id,
                    "template_id": sb.template_id,
                    "state": sb.state,
                    "started_at": sb.started_at,
                }
                for sb in sandboxes
            ])
        else:
            if not sandboxes:
                output_text("No sandboxes found")
                return

            # Prepare table data
            headers = ["Sandbox ID", "Template", "State", "Started At"]
            rows = [
                [sb.sandbox_id, sb.template_id, sb.state, sb.started_at]
                for sb in sandboxes
            ]

            output_table(headers, rows)
    except Exception as e:
        output_error(f"Failed to list sandboxes: {str(e)}")


@sandbox.command("get-host")
@click.argument("sandbox_id", required=False)
def get_host(sandbox_id):
    """Get the container hostname for a sandbox.

    Examples:
        sandbox get-host sb_123abc
        sandbox get-host  # Uses last active sandbox
    """
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        if not sandbox_id:
            output_error("No sandbox ID provided and no active sandbox found")
            return

        sb = Sandbox.connect(sandbox_id)

        # Assuming the Sandbox class has a method to get hostname
        # If not, we can get it from the info metadata
        sandbox_info = sb.get_info()

        # Try to get hostname from metadata or use sandbox_id as fallback
        hostname = sandbox_info.metadata.get("hostname", sandbox_id) if sandbox_info.metadata else sandbox_id

        output_text(hostname)
    except Exception as e:
        output_error(f"Failed to get sandbox hostname: {str(e)}")
