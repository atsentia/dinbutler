"""Tests for Sandbox class."""

import pytest
from dinbutler import Sandbox, SandboxException, NotFoundException


class TestSandboxLifecycle:
    """Test sandbox lifecycle operations."""

    def test_create_sandbox(self):
        """Test creating a sandbox."""
        sandbox = Sandbox.create(template="default", timeout=60)

        assert sandbox.sandbox_id is not None
        assert sandbox.sandbox_id.startswith("sandbox-")
        assert sandbox.is_running()

        sandbox.kill()
        assert not sandbox.is_running()

    def test_create_sandbox_with_context_manager(self):
        """Test sandbox with context manager."""
        with Sandbox.create(timeout=60) as sandbox:
            assert sandbox.is_running()
            sandbox_id = sandbox.sandbox_id

        # Should be killed after context
        manager = sandbox._manager
        assert not manager.is_running(sandbox_id)

    def test_create_sandbox_with_envs(self):
        """Test creating sandbox with environment variables."""
        with Sandbox.create(envs={"MY_VAR": "test_value"}) as sandbox:
            result = sandbox.commands.run("echo $MY_VAR")
            assert "test_value" in result.stdout

    def test_create_sandbox_with_metadata(self):
        """Test creating sandbox with metadata."""
        metadata = {"project": "test", "owner": "pytest"}
        sandbox = Sandbox.create(metadata=metadata)

        info = sandbox.get_info()
        assert info.metadata.get("project") == "test"

        sandbox.kill()

    def test_connect_to_sandbox(self):
        """Test connecting to existing sandbox."""
        sandbox1 = Sandbox.create()
        sandbox_id = sandbox1.sandbox_id

        sandbox2 = Sandbox.connect(sandbox_id)
        assert sandbox2.sandbox_id == sandbox_id
        assert sandbox2.is_running()

        sandbox1.kill()

    def test_connect_nonexistent_sandbox(self):
        """Test connecting to non-existent sandbox."""
        with pytest.raises(NotFoundException):
            Sandbox.connect("nonexistent-sandbox-id")

    def test_list_sandboxes(self):
        """Test listing sandboxes."""
        sandbox1 = Sandbox.create()
        sandbox2 = Sandbox.create()

        sandboxes = Sandbox.list()
        ids = [s.sandbox_id for s in sandboxes]

        assert sandbox1.sandbox_id in ids
        assert sandbox2.sandbox_id in ids

        sandbox1.kill()
        sandbox2.kill()


class TestSandboxCommands:
    """Test command execution."""

    def test_run_simple_command(self):
        """Test running a simple command."""
        with Sandbox.create() as sandbox:
            result = sandbox.commands.run("echo hello")
            assert "hello" in result.stdout
            assert result.exit_code == 0

    def test_run_command_with_stderr(self):
        """Test command with stderr output."""
        with Sandbox.create() as sandbox:
            result = sandbox.commands.run("echo error >&2")
            assert "error" in result.stderr

    def test_run_command_with_exit_code(self):
        """Test command with non-zero exit code."""
        with Sandbox.create() as sandbox:
            result = sandbox.commands.run("exit 42")
            assert result.exit_code == 42

    def test_run_command_with_cwd(self):
        """Test command with working directory."""
        with Sandbox.create() as sandbox:
            result = sandbox.commands.run("pwd", cwd="/tmp")
            assert "/tmp" in result.stdout

    def test_run_command_with_envs(self):
        """Test command with custom environment."""
        with Sandbox.create() as sandbox:
            result = sandbox.commands.run(
                "echo $TEST_VAR",
                envs={"TEST_VAR": "custom_value"}
            )
            assert "custom_value" in result.stdout

    def test_list_processes(self):
        """Test listing processes."""
        with Sandbox.create() as sandbox:
            processes = sandbox.commands.list()
            # Should at least have the sleep infinity process
            assert len(processes) > 0
            pids = [p.pid for p in processes]
            assert all(pid > 0 for pid in pids)


class TestSandboxFilesystem:
    """Test filesystem operations."""

    def test_write_and_read_file(self):
        """Test writing and reading a file."""
        with Sandbox.create() as sandbox:
            content = "Hello, World!"
            sandbox.files.write("/tmp/test.txt", content)

            read_content = sandbox.files.read("/tmp/test.txt")
            assert read_content == content

    def test_write_binary_content(self):
        """Test writing binary content."""
        with Sandbox.create() as sandbox:
            content = "Binary: \x00\x01\x02"
            sandbox.files.write("/tmp/binary.txt", content)

            read_content = sandbox.files.read("/tmp/binary.txt")
            # Note: might be encoded/decoded differently
            assert "Binary" in read_content

    def test_file_exists(self):
        """Test checking file existence."""
        with Sandbox.create() as sandbox:
            sandbox.files.write("/tmp/exists.txt", "test")

            assert sandbox.files.exists("/tmp/exists.txt")
            assert not sandbox.files.exists("/tmp/nonexistent.txt")

    def test_list_directory(self):
        """Test listing directory contents."""
        with Sandbox.create() as sandbox:
            sandbox.files.write("/tmp/file1.txt", "a")
            sandbox.files.write("/tmp/file2.txt", "b")

            entries = sandbox.files.list("/tmp")
            names = [e.name for e in entries]

            assert "file1.txt" in names
            assert "file2.txt" in names

    def test_remove_file(self):
        """Test removing a file."""
        with Sandbox.create() as sandbox:
            sandbox.files.write("/tmp/to_delete.txt", "delete me")
            assert sandbox.files.exists("/tmp/to_delete.txt")

            sandbox.files.remove("/tmp/to_delete.txt")
            assert not sandbox.files.exists("/tmp/to_delete.txt")

    def test_get_file_info(self):
        """Test getting file info."""
        with Sandbox.create() as sandbox:
            sandbox.files.write("/tmp/info.txt", "test content")

            info = sandbox.files.get_info("/tmp/info.txt")
            assert info.name == "info.txt"
            assert info.size > 0
            assert info.type.value == "file"

    def test_read_nonexistent_file(self):
        """Test reading non-existent file."""
        with Sandbox.create() as sandbox:
            with pytest.raises(NotFoundException):
                sandbox.files.read("/tmp/nonexistent.txt")


class TestSandboxPty:
    """Test PTY operations."""

    def test_create_pty(self):
        """Test creating a PTY session."""
        with Sandbox.create() as sandbox:
            pty = sandbox.pty.create()

            assert pty.exec_id is not None
            assert pty.is_running()

            pty.kill()

    def test_pty_send_command(self):
        """Test sending command to PTY."""
        with Sandbox.create() as sandbox:
            with sandbox.pty.create() as pty:
                pty.send_stdin("echo hello\n")

                # Wait briefly for output
                import time
                time.sleep(0.5)

                output = pty.read_all()
                # PTY output includes echoed input
                assert b"hello" in output or b"echo" in output


# Run tests with: pytest tests/test_sandbox.py -v
