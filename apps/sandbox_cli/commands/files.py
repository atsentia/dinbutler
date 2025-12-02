import click
import sys
from pathlib import Path
from dinbutler import Sandbox
from apps.sandbox_cli.modules.state import get_sandbox_id_or_arg
from apps.sandbox_cli.modules.output import output_json, output_text, output_error, output_success, output_table


@click.group()
def files():
    """File operations in sandboxes."""
    pass


@files.command()
@click.argument('sandbox_id', required=False)
@click.argument('path', default='/')
@click.option('--depth', default=1, help='Directory traversal depth')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def ls(sandbox_id, path, depth, as_json):
    """List directory contents."""
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        sandbox = Sandbox(sandbox_id)

        entries = sandbox.files.list(path, depth=depth)

        if as_json:
            data = [
                {
                    'name': e.name,
                    'path': e.path,
                    'type': e.type,
                    'size': e.size,
                    'mode': e.mode,
                    'permissions': e.permissions
                }
                for e in entries
            ]
            output_json(data)
        else:
            headers = ['Name', 'Type', 'Size', 'Permissions']
            rows = [
                [e.name, e.type, str(e.size) if e.size else '-', e.permissions]
                for e in entries
            ]
            output_table(headers, rows)
    except Exception as e:
        output_error(f"Failed to list directory: {e}")
        sys.exit(1)


@files.command()
@click.argument('sandbox_id', required=False)
@click.argument('path')
@click.option('--format', 'fmt', type=click.Choice(['text', 'bytes']), default='text', help='Read format')
def read(sandbox_id, path, fmt):
    """Read file contents."""
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        sandbox = Sandbox(sandbox_id)

        content = sandbox.files.read(path, format=fmt)

        if fmt == 'bytes':
            sys.stdout.buffer.write(content)
        else:
            output_text(content)
    except Exception as e:
        output_error(f"Failed to read file: {e}")
        sys.exit(1)


@files.command()
@click.argument('sandbox_id', required=False)
@click.argument('path')
@click.argument('content', required=False)
@click.option('--stdin', is_flag=True, help='Read content from stdin')
def write(sandbox_id, path, content, stdin):
    """Write content to file."""
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        sandbox = Sandbox(sandbox_id)

        if stdin:
            content = sys.stdin.read()
        elif content is None:
            output_error("Either provide content as argument or use --stdin")
            sys.exit(1)

        result = sandbox.files.write(path, content)
        output_success(f"Wrote {result.bytes_written} bytes to {path}")
    except Exception as e:
        output_error(f"Failed to write file: {e}")
        sys.exit(1)


@files.command()
@click.argument('sandbox_id', required=False)
@click.argument('path')
def exists(sandbox_id, path):
    """Check if path exists."""
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        sandbox = Sandbox(sandbox_id)

        exists = sandbox.files.exists(path)

        if exists:
            output_success(f"Path exists: {path}")
            sys.exit(0)
        else:
            output_text(f"Path does not exist: {path}")
            sys.exit(1)
    except Exception as e:
        output_error(f"Failed to check path: {e}")
        sys.exit(1)


@files.command()
@click.argument('sandbox_id', required=False)
@click.argument('path')
def remove(sandbox_id, path):
    """Remove file or directory."""
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        sandbox = Sandbox(sandbox_id)

        sandbox.files.remove(path)
        output_success(f"Removed: {path}")
    except Exception as e:
        output_error(f"Failed to remove path: {e}")
        sys.exit(1)


@files.command()
@click.argument('sandbox_id', required=False)
@click.argument('path')
def mkdir(sandbox_id, path):
    """Create directory."""
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        sandbox = Sandbox(sandbox_id)

        # Use write with empty content to create directory structure
        # Or use mkdir if available in the API
        parent = str(Path(path).parent)
        sandbox.files.write(f"{path}/.gitkeep", "")
        output_success(f"Created directory: {path}")
    except Exception as e:
        output_error(f"Failed to create directory: {e}")
        sys.exit(1)


@files.command()
@click.argument('sandbox_id', required=False)
@click.argument('path')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def info(sandbox_id, path, as_json):
    """Get file metadata."""
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        sandbox = Sandbox(sandbox_id)

        entry = sandbox.files.get_info(path)

        if as_json:
            data = {
                'name': entry.name,
                'path': entry.path,
                'type': entry.type,
                'size': entry.size,
                'mode': entry.mode,
                'permissions': entry.permissions
            }
            output_json(data)
        else:
            output_text(f"Name: {entry.name}")
            output_text(f"Path: {entry.path}")
            output_text(f"Type: {entry.type}")
            output_text(f"Size: {entry.size if entry.size else 'N/A'}")
            output_text(f"Mode: {entry.mode}")
            output_text(f"Permissions: {entry.permissions}")
    except Exception as e:
        output_error(f"Failed to get file info: {e}")
        sys.exit(1)


@files.command()
@click.argument('sandbox_id', required=False)
@click.argument('old_path')
@click.argument('new_path')
def rename(sandbox_id, old_path, new_path):
    """Rename or move file."""
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        sandbox = Sandbox(sandbox_id)

        # Read old file
        content = sandbox.files.read(old_path, format='bytes')

        # Write to new location
        sandbox.files.write(new_path, content)

        # Remove old file
        sandbox.files.remove(old_path)

        output_success(f"Renamed: {old_path} -> {new_path}")
    except Exception as e:
        output_error(f"Failed to rename file: {e}")
        sys.exit(1)


@files.command()
@click.argument('sandbox_id', required=False)
@click.argument('local_path')
@click.argument('remote_path')
def upload(sandbox_id, local_path, remote_path):
    """Upload local file to sandbox."""
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        sandbox = Sandbox(sandbox_id)

        local_file = Path(local_path)
        if not local_file.exists():
            output_error(f"Local file not found: {local_path}")
            sys.exit(1)

        # Read local file
        if local_file.is_file():
            with open(local_file, 'rb') as f:
                content = f.read()

            # Write to sandbox
            result = sandbox.files.write(remote_path, content)
            output_success(f"Uploaded {result.bytes_written} bytes to {remote_path}")
        else:
            output_error(f"Path is not a file: {local_path}")
            sys.exit(1)
    except Exception as e:
        output_error(f"Failed to upload file: {e}")
        sys.exit(1)


@files.command()
@click.argument('sandbox_id', required=False)
@click.argument('remote_path')
@click.argument('local_path')
def download(sandbox_id, remote_path, local_path):
    """Download file from sandbox."""
    try:
        sandbox_id = get_sandbox_id_or_arg(sandbox_id)
        sandbox = Sandbox(sandbox_id)

        # Read from sandbox
        content = sandbox.files.read(remote_path, format='bytes')

        # Write to local file
        local_file = Path(local_path)
        local_file.parent.mkdir(parents=True, exist_ok=True)

        with open(local_file, 'wb') as f:
            f.write(content)

        output_success(f"Downloaded {len(content)} bytes to {local_path}")
    except Exception as e:
        output_error(f"Failed to download file: {e}")
        sys.exit(1)
