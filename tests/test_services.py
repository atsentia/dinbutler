"""Tests for service classes."""

import pytest
from dinbutler.services.docker_client import DockerClient, get_docker_client
from dinbutler.services.sandbox_manager import SandboxManager
from dinbutler.services.filesystem import FilesystemService
from dinbutler.services.commands import CommandsService


class TestDockerClient:
    """Test Docker client."""

    def test_get_docker_client(self):
        """Test getting Docker client singleton."""
        client1 = get_docker_client()
        client2 = get_docker_client()

        assert client1 is client2

    def test_ping(self):
        """Test Docker ping."""
        client = get_docker_client()
        assert client.ping() is True


class TestSandboxManager:
    """Test sandbox manager."""

    def test_create_and_kill(self):
        """Test creating and killing sandbox."""
        manager = SandboxManager()

        info = manager.create(timeout=60)
        assert info.sandbox_id.startswith("sandbox-")
        assert manager.is_running(info.sandbox_id)

        success = manager.kill(info.sandbox_id)
        assert success
        assert not manager.is_running(info.sandbox_id)

    def test_list_sandboxes(self):
        """Test listing sandboxes."""
        manager = SandboxManager()

        info1 = manager.create(timeout=60)
        info2 = manager.create(timeout=60)

        sandboxes = manager.list()
        ids = [s.sandbox_id for s in sandboxes]

        assert info1.sandbox_id in ids
        assert info2.sandbox_id in ids

        manager.kill(info1.sandbox_id)
        manager.kill(info2.sandbox_id)


class TestFilesystemService:
    """Test filesystem service."""

    def test_write_and_read(self, sandbox):
        """Test writing and reading files."""
        service = FilesystemService()

        service.write(sandbox.sandbox_id, "/tmp/test.txt", "hello")
        content = service.read(sandbox.sandbox_id, "/tmp/test.txt")

        assert content == "hello"


class TestCommandsService:
    """Test commands service."""

    def test_run_command(self, sandbox):
        """Test running a command."""
        service = CommandsService()

        result = service.run(sandbox.sandbox_id, "echo test")

        assert "test" in result.stdout
        assert result.exit_code == 0
