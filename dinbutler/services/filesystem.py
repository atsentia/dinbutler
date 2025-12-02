"""Filesystem operations inside sandbox containers."""

import os
import stat
import logging
from datetime import datetime
from typing import Optional, List, Union, Iterator, Callable, Any
from pathlib import Path
import asyncio
from threading import Thread, Event

from dinbutler.services.docker_client import DockerClient, get_docker_client
from dinbutler.models.filesystem import (
    EntryInfo,
    WriteInfo,
    FileType,
    FilesystemEvent,
    FilesystemEventType,
)
from dinbutler.exceptions import (
    SandboxException,
    NotFoundException,
    TimeoutException,
)

logger = logging.getLogger(__name__)


class WatchHandle:
    """Handle for watching filesystem changes."""

    def __init__(
        self,
        sandbox_id: str,
        path: str,
        docker: DockerClient,
        exec_id: str,
    ):
        self._sandbox_id = sandbox_id
        self._path = path
        self._docker = docker
        self._exec_id = exec_id
        self._events: List[FilesystemEvent] = []
        self._stopped = Event()
        self._thread: Optional[Thread] = None

    def _start_watching(self, stream: Iterator[bytes]) -> None:
        """Background thread to collect events."""
        try:
            for chunk in stream:
                if self._stopped.is_set():
                    break
                event = self._parse_inotify_output(chunk.decode())
                if event:
                    self._events.append(event)
        except Exception as e:
            logger.debug(f"Watch stream ended: {e}")

    def _parse_inotify_output(self, line: str) -> Optional[FilesystemEvent]:
        """Parse inotifywait output line."""
        # Format: directory EVENT filename
        # Example: /tmp/ CREATE test.txt
        parts = line.strip().split()
        if len(parts) >= 2:
            event_type_str = parts[1] if len(parts) > 1 else ""
            filename = parts[2] if len(parts) > 2 else ""

            event_map = {
                "CREATE": FilesystemEventType.CREATE,
                "MODIFY": FilesystemEventType.MODIFY,
                "DELETE": FilesystemEventType.DELETE,
                "MOVED_FROM": FilesystemEventType.DELETE,
                "MOVED_TO": FilesystemEventType.CREATE,
                "ATTRIB": FilesystemEventType.CHMOD,
            }

            for key, event_type in event_map.items():
                if key in event_type_str:
                    return FilesystemEvent(name=filename, type=event_type)
        return None

    def get_new_events(self) -> List[FilesystemEvent]:
        """Get new events since last call."""
        events = self._events.copy()
        self._events.clear()
        return events

    def stop(self) -> None:
        """Stop watching."""
        self._stopped.set()
        try:
            # Kill the inotifywait process
            self._docker.exec_run(
                self._sandbox_id,
                f"pkill -f 'inotifywait.*{self._path}'"
            )
        except Exception:
            pass


class FilesystemService:
    """File operations inside sandbox containers."""

    def __init__(self, docker_client: Optional[DockerClient] = None):
        self._docker = docker_client or get_docker_client()

    def _get_container_name(self, sandbox_id: str) -> str:
        """Get Docker container name for sandbox."""
        return f"e2b-{sandbox_id}"

    def read(
        self,
        sandbox_id: str,
        path: str,
        format: str = "text",
        user: Optional[str] = None,
        request_timeout: Optional[float] = None,
    ) -> Union[str, bytes, Iterator[bytes]]:
        """Read file content from sandbox.

        Args:
            sandbox_id: The sandbox ID.
            path: Path to the file.
            format: "text", "bytes", or "stream".
            user: User to read as (default: container user).
            request_timeout: Timeout for the operation.

        Returns:
            File content as string, bytes, or iterator.

        Raises:
            NotFoundException: If file doesn't exist.
        """
        container_name = self._get_container_name(sandbox_id)

        # Check if file exists first
        if not self.exists(sandbox_id, path, user):
            raise NotFoundException(f"File not found: {path}", sandbox_id=sandbox_id)

        try:
            # Use docker cp for efficiency
            content = self._docker.copy_from_container(container_name, path)

            if format == "bytes":
                return content
            elif format == "stream":
                def stream_content():
                    chunk_size = 8192
                    for i in range(0, len(content), chunk_size):
                        yield content[i:i+chunk_size]
                return stream_content()
            else:  # text
                return content.decode("utf-8")

        except Exception as e:
            raise SandboxException(f"Failed to read file: {e}", sandbox_id=sandbox_id)

    def write(
        self,
        sandbox_id: str,
        path: str,
        data: Union[str, bytes],
        user: Optional[str] = None,
        request_timeout: Optional[float] = None,
    ) -> WriteInfo:
        """Write content to file in sandbox.

        Args:
            sandbox_id: The sandbox ID.
            path: Path to the file.
            data: Content to write (string or bytes).
            user: User to write as.
            request_timeout: Timeout for the operation.

        Returns:
            WriteInfo with file details.
        """
        container_name = self._get_container_name(sandbox_id)

        try:
            # Ensure parent directory exists
            parent = str(Path(path).parent)
            self._docker.exec_run(
                container_name,
                f"mkdir -p {parent}",
                user=user,
            )

            # Write using base64 encoding for binary safety
            import base64
            b64_content = base64.b64encode(
                data.encode() if isinstance(data, str) else data
            ).decode()

            self._docker.exec_run(
                container_name,
                f"sh -c 'echo {b64_content} | base64 -d > {path}'",
                user=user,
            )

            # Get file info
            name = Path(path).name
            file_type = FileType.FILE

            return WriteInfo(name=name, path=path, type=file_type)

        except Exception as e:
            raise SandboxException(f"Failed to write file: {e}", sandbox_id=sandbox_id)

    def list(
        self,
        sandbox_id: str,
        path: str,
        depth: int = 1,
        user: Optional[str] = None,
        request_timeout: Optional[float] = None,
    ) -> List[EntryInfo]:
        """List directory contents.

        Args:
            sandbox_id: The sandbox ID.
            path: Directory path.
            depth: Maximum depth (1 = immediate children only).
            user: User to list as.
            request_timeout: Timeout for the operation.

        Returns:
            List of EntryInfo objects.
        """
        container_name = self._get_container_name(sandbox_id)

        try:
            # Use ls with detailed output
            # Format: permissions links owner group size month day time name
            result = self._docker.exec_run(
                container_name,
                f"ls -la --time-style=+%s {path}",
                user=user,
                demux=True,
            )

            stdout = result.output[0].decode() if result.output[0] else ""
            entries = []

            for line in stdout.strip().split("\n"):
                if line.startswith("total") or not line.strip():
                    continue

                parts = line.split()
                if len(parts) < 7:
                    continue

                perms = parts[0]
                owner = parts[2]
                group = parts[3]
                size = int(parts[4]) if parts[4].isdigit() else 0
                timestamp = int(parts[5]) if parts[5].isdigit() else 0
                name = " ".join(parts[6:])

                # Skip . and ..
                if name in (".", ".."):
                    continue

                # Determine file type
                if perms.startswith("d"):
                    file_type = FileType.DIR
                elif perms.startswith("l"):
                    file_type = FileType.SYMLINK
                else:
                    file_type = FileType.FILE

                # Parse permissions (convert to octal)
                mode = self._parse_permissions_to_mode(perms)

                entry = EntryInfo(
                    name=name,
                    path=str(Path(path) / name),
                    type=file_type,
                    size=size,
                    mode=mode,
                    permissions=perms[1:10],  # rwxr-xr-x format
                    owner=owner,
                    group=group,
                    modified_time=datetime.fromtimestamp(timestamp),
                )
                entries.append(entry)

            return entries

        except Exception as e:
            raise SandboxException(f"Failed to list directory: {e}", sandbox_id=sandbox_id)

    def _parse_permissions_to_mode(self, perms: str) -> int:
        """Convert ls permissions string to mode integer."""
        mode = 0
        if len(perms) >= 10:
            # Owner
            if perms[1] == 'r': mode |= stat.S_IRUSR
            if perms[2] == 'w': mode |= stat.S_IWUSR
            if perms[3] == 'x': mode |= stat.S_IXUSR
            # Group
            if perms[4] == 'r': mode |= stat.S_IRGRP
            if perms[5] == 'w': mode |= stat.S_IWGRP
            if perms[6] == 'x': mode |= stat.S_IXGRP
            # Other
            if perms[7] == 'r': mode |= stat.S_IROTH
            if perms[8] == 'w': mode |= stat.S_IWOTH
            if perms[9] == 'x': mode |= stat.S_IXOTH
        return mode

    def exists(
        self,
        sandbox_id: str,
        path: str,
        user: Optional[str] = None,
    ) -> bool:
        """Check if path exists.

        Args:
            sandbox_id: The sandbox ID.
            path: Path to check.
            user: User to check as.

        Returns:
            True if exists, False otherwise.
        """
        container_name = self._get_container_name(sandbox_id)

        try:
            result = self._docker.exec_run(
                container_name,
                f"test -e {path}",
                user=user,
            )
            return result.exit_code == 0
        except Exception:
            return False

    def get_info(
        self,
        sandbox_id: str,
        path: str,
        user: Optional[str] = None,
    ) -> EntryInfo:
        """Get detailed file/directory info.

        Args:
            sandbox_id: The sandbox ID.
            path: Path to file/directory.
            user: User to stat as.

        Returns:
            EntryInfo with file details.

        Raises:
            NotFoundException: If path doesn't exist.
        """
        container_name = self._get_container_name(sandbox_id)

        if not self.exists(sandbox_id, path, user):
            raise NotFoundException(f"Path not found: {path}", sandbox_id=sandbox_id)

        try:
            result = self._docker.exec_run(
                container_name,
                f"stat --format='%F|%s|%a|%U|%G|%Y|%N' {path}",
                user=user,
                demux=True,
            )

            stdout = result.output[0].decode().strip() if result.output[0] else ""
            parts = stdout.split("|")

            if len(parts) >= 6:
                type_str = parts[0]
                size = int(parts[1])
                mode = int(parts[2], 8)
                owner = parts[3]
                group = parts[4]
                mtime = int(parts[5])

                if "directory" in type_str:
                    file_type = FileType.DIR
                elif "link" in type_str:
                    file_type = FileType.SYMLINK
                else:
                    file_type = FileType.FILE

                # Convert mode to permission string
                perms = stat.filemode(mode)[1:]

                return EntryInfo(
                    name=Path(path).name,
                    path=path,
                    type=file_type,
                    size=size,
                    mode=mode,
                    permissions=perms,
                    owner=owner,
                    group=group,
                    modified_time=datetime.fromtimestamp(mtime),
                )

            raise SandboxException(f"Failed to parse stat output: {stdout}")

        except NotFoundException:
            raise
        except Exception as e:
            raise SandboxException(f"Failed to get file info: {e}", sandbox_id=sandbox_id)

    def remove(
        self,
        sandbox_id: str,
        path: str,
        user: Optional[str] = None,
    ) -> None:
        """Remove file or directory.

        Args:
            sandbox_id: The sandbox ID.
            path: Path to remove.
            user: User to remove as.
        """
        container_name = self._get_container_name(sandbox_id)

        try:
            result = self._docker.exec_run(
                container_name,
                f"rm -rf {path}",
                user=user,
            )

            if result.exit_code != 0:
                stderr = result.output[1].decode() if result.output[1] else ""
                raise SandboxException(f"Failed to remove: {stderr}")

        except SandboxException:
            raise
        except Exception as e:
            raise SandboxException(f"Failed to remove path: {e}", sandbox_id=sandbox_id)

    def watch(
        self,
        sandbox_id: str,
        path: str,
        on_change: Optional[Callable[[FilesystemEvent], None]] = None,
        recursive: bool = False,
    ) -> WatchHandle:
        """Watch directory for changes.

        Args:
            sandbox_id: The sandbox ID.
            path: Directory to watch.
            on_change: Callback for each event.
            recursive: Watch subdirectories.

        Returns:
            WatchHandle to manage the watch.
        """
        container_name = self._get_container_name(sandbox_id)

        try:
            # Check if inotifywait is available
            result = self._docker.exec_run(container_name, "which inotifywait")
            if result.exit_code != 0:
                logger.warning("inotifywait not available, falling back to polling")
                return self._watch_polling(sandbox_id, path, on_change)

            # Start inotifywait
            recursive_flag = "-r" if recursive else ""
            cmd = f"inotifywait -m {recursive_flag} -e modify,create,delete,move {path}"

            exec_id = self._docker.exec_create(
                container_name,
                cmd,
                tty=False,
            )

            stream = self._docker.exec_start(exec_id, stream=True)

            handle = WatchHandle(
                sandbox_id=sandbox_id,
                path=path,
                docker=self._docker,
                exec_id=exec_id,
            )

            # Start background thread
            thread = Thread(target=handle._start_watching, args=(stream,), daemon=True)
            thread.start()
            handle._thread = thread

            return handle

        except Exception as e:
            raise SandboxException(f"Failed to start watch: {e}", sandbox_id=sandbox_id)

    def _watch_polling(
        self,
        sandbox_id: str,
        path: str,
        on_change: Optional[Callable[[FilesystemEvent], None]] = None,
        interval: float = 1.0,
    ) -> WatchHandle:
        """Polling-based file watching fallback."""
        # Simplified polling implementation
        # In production, this would track file mtimes
        raise SandboxException(
            "Polling-based watch not implemented. "
            "Ensure inotify-tools is installed in template."
        )


# Global service instance
_filesystem_service: Optional[FilesystemService] = None


def get_filesystem_service() -> FilesystemService:
    """Get or create the global filesystem service instance."""
    global _filesystem_service
    if _filesystem_service is None:
        _filesystem_service = FilesystemService()
    return _filesystem_service
