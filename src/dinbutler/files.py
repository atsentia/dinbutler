"""File system operations for sandbox environments."""

import tarfile
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dinbutler.sandbox import Sandbox


@dataclass
class FileInfo:
    """Information about a file in the sandbox."""

    name: str
    path: str
    is_dir: bool
    size: int = 0


class SandboxFiles:
    """File operations for a sandbox container."""

    def __init__(self, sandbox: "Sandbox") -> None:
        self._sandbox = sandbox

    def write(self, path: str, content: str | bytes) -> None:
        """Write content to a file in the sandbox.

        Args:
            path: Absolute path in the sandbox
            content: String or bytes content to write
        """
        container = self._sandbox._get_container()
        if container is None:
            raise RuntimeError("Sandbox container is not running")

        if isinstance(content, str):
            content = content.encode("utf-8")

        # Create a tar archive with the file
        tar_stream = BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            file_data = BytesIO(content)
            tarinfo = tarfile.TarInfo(name=path.lstrip("/"))
            tarinfo.size = len(content)
            tar.addfile(tarinfo, file_data)

        tar_stream.seek(0)
        container.put_archive("/", tar_stream)

    def read(self, path: str) -> str:
        """Read content from a file in the sandbox.

        Args:
            path: Absolute path in the sandbox

        Returns:
            File content as string
        """
        container = self._sandbox._get_container()
        if container is None:
            raise RuntimeError("Sandbox container is not running")

        bits, _ = container.get_archive(path)
        tar_stream = BytesIO()
        for chunk in bits:
            tar_stream.write(chunk)
        tar_stream.seek(0)

        with tarfile.open(fileobj=tar_stream) as tar:
            members = tar.getmembers()
            if not members:
                raise FileNotFoundError(f"File not found: {path}")
            f = tar.extractfile(members[0])
            if f is None:
                raise FileNotFoundError(f"File not found: {path}")
            return f.read().decode("utf-8")

    def list(self, path: str = "/") -> list[FileInfo]:
        """List files in a directory in the sandbox.

        Args:
            path: Directory path to list

        Returns:
            List of FileInfo objects
        """
        container = self._sandbox._get_container()
        if container is None:
            raise RuntimeError("Sandbox container is not running")

        result = container.exec_run(["ls", "-la", path])
        if result.exit_code != 0:
            raise FileNotFoundError(f"Directory not found: {path}")

        files: list[FileInfo] = []
        lines = result.output.decode("utf-8").strip().split("\n")

        for line in lines[1:]:  # Skip the 'total' line
            parts = line.split(maxsplit=8)
            if len(parts) >= 9:
                name = parts[8]
                if name in (".", ".."):
                    continue
                is_dir = parts[0].startswith("d")
                try:
                    size = int(parts[4])
                except ValueError:
                    size = 0
                full_path = f"{path.rstrip('/')}/{name}"
                files.append(FileInfo(name=name, path=full_path, is_dir=is_dir, size=size))

        return files

    def remove(self, path: str) -> None:
        """Remove a file or directory from the sandbox.

        Args:
            path: Path to remove
        """
        container = self._sandbox._get_container()
        if container is None:
            raise RuntimeError("Sandbox container is not running")

        result = container.exec_run(["rm", "-rf", path])
        if result.exit_code != 0:
            raise OSError(f"Failed to remove: {path}")

    def exists(self, path: str) -> bool:
        """Check if a path exists in the sandbox.

        Args:
            path: Path to check

        Returns:
            True if path exists
        """
        container = self._sandbox._get_container()
        if container is None:
            raise RuntimeError("Sandbox container is not running")

        result = container.exec_run(["test", "-e", path])
        return bool(result.exit_code == 0)

    def mkdir(self, path: str, parents: bool = True) -> None:
        """Create a directory in the sandbox.

        Args:
            path: Directory path to create
            parents: If True, create parent directories as needed
        """
        container = self._sandbox._get_container()
        if container is None:
            raise RuntimeError("Sandbox container is not running")

        cmd = ["mkdir"]
        if parents:
            cmd.append("-p")
        cmd.append(path)

        result = container.exec_run(cmd)
        if result.exit_code != 0:
            raise OSError(f"Failed to create directory: {path}")
