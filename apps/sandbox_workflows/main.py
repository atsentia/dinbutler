"""
Main CLI entry point for the obox command.

Usage:
    obox https://github.com/user/repo --branch main --forks 3 --model sonnet --prompt "Add unit tests"
"""

import click
import sys
from pathlib import Path

from .modules.constants import DEFAULT_FORKS, MAX_FORKS, DEFAULT_MODEL
from .modules.logs import setup_logging
from .commands.fork import fork_command


@click.group()
@click.version_option(version="0.1.0", prog_name="obox")
def cli():
    """
    DinButler Sandbox Workflows - Orchestrate parallel agent forks with security controls.
    """
    pass


@cli.command(name="fork")
@click.argument("repo_url", required=False)
@click.option(
    "--branch",
    "-b",
    default="main",
    help="Branch to check out (default: main)",
)
@click.option(
    "--forks",
    "-f",
    default=DEFAULT_FORKS,
    type=click.IntRange(1, MAX_FORKS),
    help=f"Number of parallel forks (1-{MAX_FORKS}, default: {DEFAULT_FORKS})",
)
@click.option(
    "--model",
    "-m",
    default=DEFAULT_MODEL,
    type=click.Choice(["sonnet", "opus", "haiku"], case_sensitive=False),
    help=f"Claude model to use (default: {DEFAULT_MODEL})",
)
@click.option(
    "--prompt",
    "-p",
    required=True,
    help="Task prompt for the agent",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--log-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Custom log directory (default: ./logs)",
)
def fork(repo_url, branch, forks, model, prompt, verbose, log_dir):
    """
    Fork a repository and run parallel agent workflows.

    If REPO_URL is not provided, operates on the current directory.

    Examples:

        # Fork a remote repo 3 times
        obox fork https://github.com/user/repo --forks 3 --prompt "Add tests"

        # Work on current directory
        obox fork --prompt "Refactor code"

        # Use a specific model
        obox fork --model opus --prompt "Optimize performance"
    """
    setup_logging(verbose=verbose)
    fork_command(
        repo_url=repo_url,
        branch=branch,
        forks=forks,
        model=model,
        prompt=prompt,
        log_dir=log_dir,
    )


# Make the fork command available directly via "obox <url>" shortcut
@cli.command(name="run", hidden=True)
@click.argument("repo_url", required=False)
@click.option("--branch", "-b", default="main")
@click.option("--forks", "-f", default=DEFAULT_FORKS, type=click.IntRange(1, MAX_FORKS))
@click.option("--model", "-m", default=DEFAULT_MODEL, type=click.Choice(["sonnet", "opus", "haiku"], case_sensitive=False))
@click.option("--prompt", "-p", required=True)
@click.option("--verbose", "-v", is_flag=True)
@click.option("--log-dir", type=click.Path(path_type=Path), default=None)
def run_shortcut(repo_url, branch, forks, model, prompt, verbose, log_dir):
    """Hidden shortcut to fork command."""
    setup_logging(verbose=verbose)
    fork_command(
        repo_url=repo_url,
        branch=branch,
        forks=forks,
        model=model,
        prompt=prompt,
        log_dir=log_dir,
    )


def main():
    """Entry point for console script."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
