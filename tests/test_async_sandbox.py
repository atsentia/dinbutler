"""Tests for AsyncSandbox class."""

import pytest
from dinbutler import AsyncSandbox


@pytest.mark.asyncio
class TestAsyncSandboxLifecycle:
    """Test async sandbox lifecycle."""

    async def test_create_async_sandbox(self):
        """Test creating async sandbox."""
        sandbox = await AsyncSandbox.create(timeout=60)

        assert sandbox.sandbox_id is not None
        assert await sandbox.is_running()

        await sandbox.kill()

    async def test_async_context_manager(self):
        """Test async context manager."""
        async with await AsyncSandbox.create() as sandbox:
            assert await sandbox.is_running()
            sandbox_id = sandbox.sandbox_id

        # Should be killed after context
        sandboxes = await AsyncSandbox.list()
        ids = [s.sandbox_id for s in sandboxes]
        assert sandbox_id not in ids


@pytest.mark.asyncio
class TestAsyncCommands:
    """Test async command execution."""

    async def test_run_command(self):
        """Test running command asynchronously."""
        async with await AsyncSandbox.create() as sandbox:
            result = await sandbox.commands.run("echo async")
            assert "async" in result.stdout


@pytest.mark.asyncio
class TestAsyncFilesystem:
    """Test async filesystem operations."""

    async def test_write_and_read(self):
        """Test async file operations."""
        async with await AsyncSandbox.create() as sandbox:
            await sandbox.files.write("/tmp/async.txt", "async content")
            content = await sandbox.files.read("/tmp/async.txt")
            assert content == "async content"
