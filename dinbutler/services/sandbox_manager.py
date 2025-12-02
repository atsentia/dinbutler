"""Sandbox lifecycle management using Docker containers."""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from threading import Timer

from dinbutler.services.docker_client import DockerClient, get_docker_client
from dinbutler.models.sandbox import SandboxInfo, SandboxState, SandboxQuery
from dinbutler.exceptions import SandboxException, NotFoundException, TimeoutException

logger = logging.getLogger(__name__)

# Container label prefix
LABEL_PREFIX = "dinbutler"


class SandboxManager:
    """Manages sandbox lifecycle using Docker containers."""

    # Default template images
    TEMPLATES = {
        "default": "dinbutler-default:latest",
        "python": "dinbutler-python:latest",
        "node": "dinbutler-node:latest",
        "gemini": "dinbutler-gemini:latest",
        "cursor": "dinbutler-cursor:latest",
    }

    def __init__(self, docker_client: Optional[DockerClient] = None):
        """Initialize sandbox manager.

        Args:
            docker_client: Optional Docker client instance.
        """
        self._docker = docker_client or get_docker_client()
        self._timeout_timers: Dict[str, Timer] = {}

    def _generate_sandbox_id(self) -> str:
        """Generate unique sandbox ID."""
        return f"sandbox-{uuid.uuid4().hex[:12]}"

    def _get_container_name(self, sandbox_id: str) -> str:
        """Get Docker container name for sandbox."""
        return f"e2b-{sandbox_id}"

    def _get_image_for_template(self, template: str) -> str:
        """Get Docker image name for template."""
        if template in self.TEMPLATES:
            return self.TEMPLATES[template]
        # Assume it's a custom image name
        return template

    def _make_labels(
        self,
        sandbox_id: str,
        template: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Create container labels for sandbox tracking."""
        labels = {
            f"{LABEL_PREFIX}.sandbox_id": sandbox_id,
            f"{LABEL_PREFIX}.template": template,
            f"{LABEL_PREFIX}.created_at": datetime.utcnow().isoformat(),
        }
        if metadata:
            for key, value in metadata.items():
                labels[f"{LABEL_PREFIX}.meta.{key}"] = value
        return labels

    def _parse_labels(self, labels: Dict[str, str]) -> Dict[str, str]:
        """Parse container labels to extract sandbox info."""
        result = {}
        for key, value in labels.items():
            if key.startswith(f"{LABEL_PREFIX}."):
                clean_key = key[len(f"{LABEL_PREFIX}."):]
                result[clean_key] = value
        return result

    def _container_to_sandbox_info(self, container) -> SandboxInfo:
        """Convert Docker container to SandboxInfo."""
        labels = self._parse_labels(container.labels)

        # Parse state
        status = container.status
        if status == "running":
            state = SandboxState.RUNNING
        elif status == "paused":
            state = SandboxState.PAUSED
        else:
            state = SandboxState.STOPPED

        # Parse timestamps
        created_at = datetime.fromisoformat(
            labels.get("created_at", datetime.utcnow().isoformat())
        )

        # Extract metadata
        metadata = {}
        for key, value in labels.items():
            if key.startswith("meta."):
                metadata[key[5:]] = value

        # Parse environment variables (Docker returns list of "KEY=VALUE" strings)
        env_list = container.attrs.get("Config", {}).get("Env", []) or []
        envs = {}
        for env_str in env_list:
            if "=" in env_str:
                key, value = env_str.split("=", 1)
                envs[key] = value

        return SandboxInfo(
            sandbox_id=labels.get("sandbox_id", container.name),
            template_id=labels.get("template", "default"),
            state=state,
            started_at=created_at,
            metadata=metadata,
            envs=envs,
        )

    def _setup_timeout(self, sandbox_id: str, timeout: int) -> None:
        """Setup auto-kill timer for sandbox."""
        if sandbox_id in self._timeout_timers:
            self._timeout_timers[sandbox_id].cancel()

        def kill_on_timeout():
            logger.info(f"Sandbox {sandbox_id} timed out after {timeout}s")
            try:
                self.kill(sandbox_id)
            except Exception as e:
                logger.error(f"Failed to kill timed-out sandbox: {e}")

        timer = Timer(timeout, kill_on_timeout)
        timer.daemon = True
        timer.start()
        self._timeout_timers[sandbox_id] = timer

    def _cancel_timeout(self, sandbox_id: str) -> None:
        """Cancel timeout timer for sandbox."""
        if sandbox_id in self._timeout_timers:
            self._timeout_timers[sandbox_id].cancel()
            del self._timeout_timers[sandbox_id]

    def create(
        self,
        template: str = "default",
        timeout: int = 300,
        envs: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> SandboxInfo:
        """Create a new sandbox.

        Args:
            template: Template name or Docker image.
            timeout: Sandbox timeout in seconds (default 5 minutes).
            envs: Environment variables for the sandbox.
            metadata: Custom metadata labels.

        Returns:
            SandboxInfo with sandbox details.

        Raises:
            SandboxException: If sandbox creation fails.
        """
        sandbox_id = self._generate_sandbox_id()
        container_name = self._get_container_name(sandbox_id)
        image = self._get_image_for_template(template)
        labels = self._make_labels(sandbox_id, template, metadata)

        logger.info(f"Creating sandbox {sandbox_id} with template {template}")

        try:
            # Ensure image exists
            if not self._docker.image_exists(image):
                # Try pulling if it's not a local template
                if template not in self.TEMPLATES:
                    logger.info(f"Pulling image {image}")
                    self._docker.pull_image(image)
                else:
                    raise SandboxException(
                        f"Template '{template}' not found. "
                        f"Build it first with: dinbutler build-template {template}"
                    )

            # Create container
            container = self._docker.create_container(
                image=image,
                name=container_name,
                envs=envs,
                labels=labels,
            )

            # Start container
            self._docker.start_container(container.id)

            # Setup timeout
            if timeout > 0:
                self._setup_timeout(sandbox_id, timeout)

            # Get fresh container info
            container = self._docker.get_container(container_name)
            return self._container_to_sandbox_info(container)

        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}")
            # Cleanup on failure
            try:
                if self._docker.container_exists(container_name):
                    self._docker.remove_container(container_name, force=True)
            except Exception:
                pass
            raise SandboxException(f"Failed to create sandbox: {e}") from e

    def connect(self, sandbox_id: str) -> SandboxInfo:
        """Connect to an existing sandbox.

        Args:
            sandbox_id: The sandbox ID to connect to.

        Returns:
            SandboxInfo with sandbox details.

        Raises:
            NotFoundException: If sandbox doesn't exist.
        """
        container_name = self._get_container_name(sandbox_id)

        if not self._docker.container_exists(container_name):
            raise NotFoundException(f"Sandbox '{sandbox_id}' not found")

        container = self._docker.get_container(container_name)
        return self._container_to_sandbox_info(container)

    def kill(self, sandbox_id: str) -> bool:
        """Kill and remove a sandbox.

        Args:
            sandbox_id: The sandbox ID to kill.

        Returns:
            True if sandbox was killed, False if it didn't exist.
        """
        container_name = self._get_container_name(sandbox_id)

        # Cancel timeout timer
        self._cancel_timeout(sandbox_id)

        if not self._docker.container_exists(container_name):
            return False

        logger.info(f"Killing sandbox {sandbox_id}")

        try:
            self._docker.stop_container(container_name, timeout=5)
        except Exception:
            pass  # Container might already be stopped

        try:
            self._docker.remove_container(container_name, force=True)
        except Exception as e:
            logger.error(f"Failed to remove container: {e}")
            return False

        return True

    def list(self, query: Optional[SandboxQuery] = None) -> List[SandboxInfo]:
        """List all sandboxes.

        Args:
            query: Optional filter query.

        Returns:
            List of SandboxInfo objects.
        """
        filters = {"label": f"{LABEL_PREFIX}.sandbox_id"}

        containers = self._docker.list_containers(all=True, filters=filters)
        sandboxes = [self._container_to_sandbox_info(c) for c in containers]

        # Apply query filters
        if query:
            if query.state:
                sandboxes = [s for s in sandboxes if s.state in query.state]
            if query.metadata:
                def matches_metadata(s: SandboxInfo) -> bool:
                    for key, value in query.metadata.items():
                        if s.metadata.get(key) != value:
                            return False
                    return True
                sandboxes = [s for s in sandboxes if matches_metadata(s)]

        return sandboxes

    def get_info(self, sandbox_id: str) -> Optional[SandboxInfo]:
        """Get sandbox information.

        Args:
            sandbox_id: The sandbox ID.

        Returns:
            SandboxInfo or None if not found.
        """
        try:
            return self.connect(sandbox_id)
        except NotFoundException:
            return None

    def is_running(self, sandbox_id: str) -> bool:
        """Check if sandbox is running.

        Args:
            sandbox_id: The sandbox ID.

        Returns:
            True if running, False otherwise.
        """
        container_name = self._get_container_name(sandbox_id)
        return self._docker.is_container_running(container_name)

    def set_timeout(self, sandbox_id: str, timeout: int) -> None:
        """Update sandbox timeout.

        Args:
            sandbox_id: The sandbox ID.
            timeout: New timeout in seconds.
        """
        if not self.is_running(sandbox_id):
            raise NotFoundException(f"Sandbox '{sandbox_id}' not found or not running")

        self._setup_timeout(sandbox_id, timeout)

    def cleanup_all(self) -> int:
        """Remove all sandboxes (cleanup utility).

        Returns:
            Number of sandboxes removed.
        """
        sandboxes = self.list()
        count = 0
        for sandbox in sandboxes:
            if self.kill(sandbox.sandbox_id):
                count += 1
        return count


# Global manager instance
_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager() -> SandboxManager:
    """Get or create the global sandbox manager instance."""
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager()
    return _sandbox_manager
