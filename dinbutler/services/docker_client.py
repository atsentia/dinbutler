"""Docker client wrapper with Colima socket auto-detection."""

import os
import docker
from docker.models.containers import Container
from docker.models.images import Image
from pathlib import Path
from typing import Optional, Dict, List, Any, Iterator, Tuple
import logging

logger = logging.getLogger(__name__)


class DockerClientError(Exception):
    """Error connecting to Docker/Colima."""
    pass


class DockerClient:
    """Wrapper around docker-py with Colima socket detection."""

    # Common Colima socket locations
    COLIMA_SOCKET_PATHS = [
        Path.home() / ".colima" / "default" / "docker.sock",
        Path.home() / ".colima" / "docker.sock",
        Path("/var/run/docker.sock"),
    ]

    def __init__(self, socket_path: Optional[str] = None):
        """Initialize Docker client.

        Args:
            socket_path: Optional explicit socket path. If not provided,
                        auto-detects Colima socket location.
        """
        self._socket_path = socket_path or self._find_socket()
        self._client: Optional[docker.DockerClient] = None
        self._api: Optional[docker.APIClient] = None

    def _find_socket(self) -> str:
        """Find the Docker/Colima socket path."""
        # Check environment variable first
        env_socket = os.environ.get("DINBUTLER_SOCKET") or os.environ.get("DOCKER_HOST")
        if env_socket:
            # Handle unix:// prefix
            if env_socket.startswith("unix://"):
                env_socket = env_socket[7:]
            if Path(env_socket).exists():
                return f"unix://{env_socket}"

        # Check common locations
        for path in self.COLIMA_SOCKET_PATHS:
            if path.exists():
                logger.debug(f"Found Docker socket at: {path}")
                return f"unix://{path}"

        raise DockerClientError(
            "Could not find Docker socket. Is Colima running?\n"
            "Start with: colima start --vm-type=vz\n"
            "Or set DINBUTLER_SOCKET environment variable."
        )

    @property
    def client(self) -> docker.DockerClient:
        """Get or create the high-level Docker client."""
        if self._client is None:
            self._client = docker.DockerClient(base_url=self._socket_path)
            # Verify connection
            try:
                self._client.ping()
            except Exception as e:
                raise DockerClientError(f"Cannot connect to Docker: {e}")
        return self._client

    @property
    def api(self) -> docker.APIClient:
        """Get or create the low-level API client (for exec operations)."""
        if self._api is None:
            self._api = docker.APIClient(base_url=self._socket_path)
        return self._api

    # Container operations

    def create_container(
        self,
        image: str,
        name: str,
        envs: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        command: str = "sleep infinity",
        working_dir: str = "/home/user",
        user: str = "user",
        network_mode: str = "bridge",
        **kwargs,
    ) -> Container:
        """Create a new container."""
        return self.client.containers.create(
            image=image,
            name=name,
            command=command,
            environment=envs or {},
            labels=labels or {},
            working_dir=working_dir,
            user=user,
            network_mode=network_mode,
            detach=True,
            tty=True,
            stdin_open=True,
            **kwargs,
        )

    def start_container(self, container_id: str) -> None:
        """Start a container."""
        container = self.client.containers.get(container_id)
        container.start()

    def stop_container(self, container_id: str, timeout: int = 10) -> None:
        """Stop a container."""
        container = self.client.containers.get(container_id)
        container.stop(timeout=timeout)

    def remove_container(self, container_id: str, force: bool = True) -> None:
        """Remove a container."""
        container = self.client.containers.get(container_id)
        container.remove(force=force)

    def get_container(self, container_id: str) -> Container:
        """Get a container by ID or name."""
        return self.client.containers.get(container_id)

    def list_containers(
        self,
        all: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Container]:
        """List containers."""
        return self.client.containers.list(all=all, filters=filters)

    def container_exists(self, container_id: str) -> bool:
        """Check if container exists."""
        try:
            self.get_container(container_id)
            return True
        except docker.errors.NotFound:
            return False

    def is_container_running(self, container_id: str) -> bool:
        """Check if container is running."""
        try:
            container = self.get_container(container_id)
            return container.status == "running"
        except docker.errors.NotFound:
            return False

    # Exec operations

    def exec_run(
        self,
        container_id: str,
        cmd: str,
        environment: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
        user: Optional[str] = None,
        demux: bool = True,
        stream: bool = False,
        **kwargs,
    ) -> Any:
        """Run a command in container and wait for result."""
        container = self.get_container(container_id)
        return container.exec_run(
            cmd,
            environment=environment,
            workdir=workdir,
            user=user,
            demux=demux,
            stream=stream,
            **kwargs,
        )

    def exec_create(
        self,
        container_id: str,
        cmd: str,
        stdin: bool = False,
        tty: bool = False,
        environment: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
        user: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Create an exec instance (returns exec_id)."""
        return self.api.exec_create(
            container_id,
            cmd,
            stdin=stdin,
            tty=tty,
            environment=environment,
            workdir=workdir,
            user=user,
            **kwargs,
        )["Id"]

    def exec_start(
        self,
        exec_id: str,
        detach: bool = False,
        stream: bool = False,
        socket: bool = False,
        tty: bool = False,
    ) -> Any:
        """Start an exec instance."""
        return self.api.exec_start(
            exec_id,
            detach=detach,
            stream=stream,
            socket=socket,
            tty=tty,
        )

    def exec_inspect(self, exec_id: str) -> Dict[str, Any]:
        """Inspect an exec instance."""
        return self.api.exec_inspect(exec_id)

    def exec_resize(self, exec_id: str, height: int, width: int) -> None:
        """Resize exec TTY."""
        self.api.exec_resize(exec_id, height=height, width=width)

    # Image operations

    def pull_image(self, image: str) -> Image:
        """Pull an image."""
        return self.client.images.pull(image)

    def build_image(
        self,
        path: str,
        tag: str,
        rm: bool = True,
        **kwargs,
    ) -> Tuple[Image, Iterator]:
        """Build an image from Dockerfile."""
        return self.client.images.build(
            path=path,
            tag=tag,
            rm=rm,
            **kwargs,
        )

    def image_exists(self, image: str) -> bool:
        """Check if image exists locally."""
        try:
            self.client.images.get(image)
            return True
        except docker.errors.ImageNotFound:
            return False

    # File operations (using docker cp)

    def copy_to_container(
        self,
        container_id: str,
        src_path: str,
        dest_path: str,
    ) -> bool:
        """Copy file/data to container."""
        container = self.get_container(container_id)
        # For simple content, use put_archive
        import tarfile
        import io

        # Create tar archive in memory
        data = src_path.encode() if isinstance(src_path, str) else src_path
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            file_data = data if isinstance(data, bytes) else data.encode()
            tarinfo = tarfile.TarInfo(name=Path(dest_path).name)
            tarinfo.size = len(file_data)
            tar.addfile(tarinfo, io.BytesIO(file_data))
        tar_stream.seek(0)

        return container.put_archive(str(Path(dest_path).parent), tar_stream)

    def copy_from_container(
        self,
        container_id: str,
        src_path: str,
    ) -> bytes:
        """Copy file from container."""
        container = self.get_container(container_id)
        bits, stat = container.get_archive(src_path)

        # Extract from tar
        import tarfile
        import io

        tar_stream = io.BytesIO()
        for chunk in bits:
            tar_stream.write(chunk)
        tar_stream.seek(0)

        with tarfile.open(fileobj=tar_stream, mode='r') as tar:
            member = tar.getmembers()[0]
            f = tar.extractfile(member)
            return f.read() if f else b""

    # Utility

    def ping(self) -> bool:
        """Check Docker daemon connectivity."""
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close client connections."""
        if self._client:
            self._client.close()
        if self._api:
            self._api.close()


# Global client instance
_docker_client: Optional[DockerClient] = None


def get_docker_client() -> DockerClient:
    """Get or create the global Docker client instance."""
    global _docker_client
    if _docker_client is None:
        _docker_client = DockerClient()
    return _docker_client
