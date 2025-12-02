"""Command execution commands for sandbox CLI."""

import click
from typing import Tuple, Optional
from dinbutler import Sandbox
from apps.sandbox_cli.modules.state import get_sandbox_id_or_arg
from apps.sandbox_cli.modules.output import output_json, output_text, output_error, output_success


@click.group(name='exec')
def exec_cmd():
    """Execute commands in sandboxes."""
    pass


@exec_cmd.command()
@click.argument('sandbox_id', required=False)
@click.argument('command', nargs=-1, required=True)
@click.option('--shell', '-s', is_flag=True, help='Execute command in shell')
@click.option('--cwd', type=str, help='Working directory for command execution')
@click.option('--root', '-r', is_flag=True, help='Run command as root user')
@click.option('--env', '-e', multiple=True, help='Environment variables (KEY=VALUE format)')
@click.option('--timeout', '-T', type=int, default=60, help='Command timeout in seconds (default: 60)')
@click.option('--background', '-b', is_flag=True, help='Run command in background')
@click.option('--json', 'json_output', is_flag=True, help='Output in JSON format')
def run(
    sandbox_id: Optional[str],
    command: Tuple[str, ...],
    shell: bool,
    cwd: Optional[str],
    root: bool,
    env: Tuple[str, ...],
    timeout: int,
    background: bool,
    json_output: bool
):
    """Execute a command in a sandbox.

    Examples:
        dinbutler exec run my-sandbox ls -la
        dinbutler exec run my-sandbox --shell "echo $HOME"
        dinbutler exec run my-sandbox --cwd /app python script.py
        dinbutler exec run my-sandbox --root apt-get update
        dinbutler exec run my-sandbox --env KEY=value --env FOO=bar env
        dinbutler exec run my-sandbox --background sleep 100
        dinbutler exec run my-sandbox --timeout 30 long-running-task
    """
    try:
        # Get sandbox ID
        sid = get_sandbox_id_or_arg(sandbox_id)
        if not sid:
            output_error("No sandbox ID provided and no default sandbox set", json_output)
            raise click.Abort()

        # Join command parts
        cmd_str = ' '.join(command)
        if not cmd_str:
            output_error("Command cannot be empty", json_output)
            raise click.Abort()

        # Wrap in shell if requested
        if shell:
            # Escape single quotes in command for shell execution
            cmd_str_escaped = cmd_str.replace("'", "'\\''")
            cmd_str = f"sh -c '{cmd_str_escaped}'"

        # Parse environment variables
        envs = None
        if env:
            envs = {}
            for env_pair in env:
                if '=' not in env_pair:
                    output_error(f"Invalid environment variable format: {env_pair} (expected KEY=VALUE)", json_output)
                    raise click.Abort()
                key, value = env_pair.split('=', 1)
                envs[key] = value

        # Get sandbox
        sandbox = Sandbox.get(sid)
        if not sandbox:
            output_error(f"Sandbox not found: {sid}", json_output)
            raise click.Abort()

        # Determine user
        user = "root" if root else None

        # Execute command
        if background:
            # Background execution
            handle = sandbox.commands.run(
                cmd_str,
                timeout=timeout,
                cwd=cwd,
                envs=envs,
                background=True,
                user=user
            )

            if json_output:
                output_json({
                    'status': 'success',
                    'sandbox_id': sid,
                    'command': cmd_str,
                    'pid': handle.pid,
                    'background': True
                })
            else:
                output_success(f"Command started in background with PID: {handle.pid}")
                output_text(f"Sandbox: {sid}")
                output_text(f"Command: {cmd_str}")
        else:
            # Synchronous execution
            result = sandbox.commands.run(
                cmd_str,
                timeout=timeout,
                cwd=cwd,
                envs=envs,
                background=False,
                user=user
            )

            if json_output:
                output_json({
                    'status': 'success' if result.exit_code == 0 else 'error',
                    'sandbox_id': sid,
                    'command': cmd_str,
                    'exit_code': result.exit_code,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'error': result.error
                })
            else:
                # Show output
                if result.stdout:
                    output_text("STDOUT:")
                    output_text(result.stdout)

                if result.stderr:
                    output_text("STDERR:")
                    output_text(result.stderr)

                # Show exit code
                if result.exit_code == 0:
                    output_success(f"Command completed successfully (exit code: {result.exit_code})")
                else:
                    output_error(f"Command failed with exit code: {result.exit_code}", False)

                # Show error if present
                if result.error:
                    output_error(f"Error: {result.error}", False)

    except click.Abort:
        raise
    except Exception as e:
        output_error(f"Failed to execute command: {str(e)}", json_output)
        raise click.Abort()
