"""DinButler CLI entry point.

Usage:
    sbx init [--template] [--timeout] [--envs]
    sbx sandbox {create|connect|kill|info|status|list|get-host}
    sbx files {ls|read|write|exists|remove|mkdir|info|rename|upload|download}
    sbx exec run <sandbox_id> <command>
    sbx cleanup
    sbx version
"""

import click
import sys
from typing import Optional, Tuple

from dinbutler import Sandbox, __version__
from apps.sandbox_cli.modules.state import (
    save_sandbox_id,
    get_sandbox_id,
    clear_state,
    get_sandbox_id_or_arg,
)
from apps.sandbox_cli.modules.output import (
    output_json,
    output_text,
    output_error,
    output_success,
    output_table,
)
from apps.sandbox_cli.commands.sandbox import sandbox
from apps.sandbox_cli.commands.files import files
from apps.sandbox_cli.commands.exec import exec_cmd


@click.group()
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def cli(ctx: click.Context, json_output: bool) -> None:
    """DinButler CLI - Your Butler for AI sandboxes.

    Manage Docker-based sandbox environments for AI agent code execution.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output


@cli.command()
@click.option("--template", "-t", default="default", help="Template name (default, python, node)")
@click.option("--timeout", "-T", default=300, type=int, help="Timeout in seconds (default 300)")
@click.option("--envs", "-e", multiple=True, help="Environment variables (KEY=VALUE)")
@click.pass_context
def init(
    ctx: click.Context,
    template: str,
    timeout: int,
    envs: Tuple[str, ...]
) -> None:
    """Initialize a new sandbox and save its ID locally.

    Creates a sandbox and stores the ID in .dinbutler/sandbox_id for use
    by subsequent commands without needing to specify the ID each time.
    """
    # Parse environment variables
    env_dict = {}
    for env in envs:
        if "=" in env:
            key, value = env.split("=", 1)
            env_dict[key] = value

    try:
        sandbox = Sandbox.create(template=template, timeout=timeout, envs=env_dict or None)
        save_sandbox_id(sandbox.sandbox_id)

        if ctx.obj.get("json"):
            output_json({
                "sandbox_id": sandbox.sandbox_id,
                "template": template,
                "timeout": timeout,
                "status": "running"
            })
        else:
            output_success(f"Sandbox created: {sandbox.sandbox_id}")
            output_text(f"  Template: {template}")
            output_text(f"  Timeout: {timeout}s")
            output_text(f"  State saved to .dinbutler/sandbox_id")
    except Exception as e:
        output_error(f"Failed to create sandbox: {e}")


@cli.command()
@click.pass_context
def cleanup(ctx: click.Context) -> None:
    """Kill all sandboxes and clear local state."""
    try:
        # Get all sandboxes
        sandboxes = Sandbox.list()
        killed = 0

        for info in sandboxes:
            try:
                sandbox = Sandbox.connect(info.sandbox_id)
                sandbox.kill()
                killed += 1
            except Exception:
                pass

        # Clear state
        clear_state()

        if ctx.obj.get("json"):
            output_json({"killed": killed, "state_cleared": True})
        else:
            output_success(f"Cleaned up {killed} sandbox(es)")
    except Exception as e:
        output_error(f"Cleanup failed: {e}")


@cli.command()
def version() -> None:
    """Show DinButler version."""
    output_text(f"dinbutler {__version__}")


# Register command groups
cli.add_command(sandbox)
cli.add_command(files)
cli.add_command(exec_cmd, name="exec")


def main() -> None:
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
