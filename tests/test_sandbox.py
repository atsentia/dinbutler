"""Unit tests for sandbox functionality.

Note: These tests require Docker to be running and accessible.
Tests are marked to skip if Docker is not available.
"""

import pytest

from dinbutler.execution import Execution
from dinbutler.files import FileInfo

# Check if Docker is available
try:
    import docker

    docker_client = docker.from_env()
    docker_client.ping()
    DOCKER_AVAILABLE = True
except Exception:
    DOCKER_AVAILABLE = False

skip_without_docker = pytest.mark.skipif(
    not DOCKER_AVAILABLE,
    reason="Docker is not available",
)


@skip_without_docker
class TestSandbox:
    """Tests for the Sandbox class."""

    def test_create_sandbox(self) -> None:
        """Test creating a sandbox."""
        from dinbutler import Sandbox

        with Sandbox.create() as sandbox:
            assert sandbox.sandbox_id is not None
            assert len(sandbox.sandbox_id) == 8

    def test_run_python_code(self) -> None:
        """Test running Python code."""
        from dinbutler import Sandbox

        with Sandbox.create() as sandbox:
            result = sandbox.run_code("print('Hello, World!')")
            assert isinstance(result, Execution)
            assert result.text == "Hello, World!"
            assert result.error is None

    def test_run_code_with_error(self) -> None:
        """Test running code that raises an error."""
        from dinbutler import Sandbox

        with Sandbox.create() as sandbox:
            result = sandbox.run_code("raise ValueError('test error')")
            assert result.error is not None
            assert result.exit_code != 0

    def test_run_bash_code(self) -> None:
        """Test running bash code."""
        from dinbutler import Sandbox

        with Sandbox.create() as sandbox:
            result = sandbox.run_code("echo 'Hello from bash'", language="bash")
            assert result.text == "Hello from bash"

    def test_run_code_with_environment(self) -> None:
        """Test running code with custom environment variables."""
        from dinbutler import Sandbox

        with Sandbox.create() as sandbox:
            result = sandbox.run_code(
                "import os; print(os.environ.get('MY_VAR', 'not set'))",
                envs={"MY_VAR": "test_value"},
            )
            assert result.text == "test_value"

    def test_file_write_and_read(self) -> None:
        """Test writing and reading files."""
        from dinbutler import Sandbox

        with Sandbox.create() as sandbox:
            sandbox.files.write("/tmp/test.txt", "Hello, File!")
            content = sandbox.files.read("/tmp/test.txt")
            assert content == "Hello, File!"

    def test_file_list(self) -> None:
        """Test listing files."""
        from dinbutler import Sandbox

        with Sandbox.create() as sandbox:
            sandbox.files.write("/tmp/file1.txt", "content1")
            sandbox.files.write("/tmp/file2.txt", "content2")
            files = sandbox.files.list("/tmp")
            names = [f.name for f in files]
            assert "file1.txt" in names
            assert "file2.txt" in names
            assert all(isinstance(f, FileInfo) for f in files)

    def test_file_exists(self) -> None:
        """Test checking file existence."""
        from dinbutler import Sandbox

        with Sandbox.create() as sandbox:
            assert not sandbox.files.exists("/tmp/nonexistent.txt")
            sandbox.files.write("/tmp/exists.txt", "content")
            assert sandbox.files.exists("/tmp/exists.txt")

    def test_command_run(self) -> None:
        """Test running shell commands."""
        from dinbutler import Sandbox

        with Sandbox.create() as sandbox:
            result = sandbox.commands.run("echo 'Hello from command'")
            assert result.stdout.strip() == "Hello from command"
            assert result.exit_code == 0

    def test_command_with_working_directory(self) -> None:
        """Test running commands with working directory."""
        from dinbutler import Sandbox

        with Sandbox.create() as sandbox:
            sandbox.files.mkdir("/tmp/workdir")
            result = sandbox.commands.run("pwd", cwd="/tmp/workdir")
            assert "/tmp/workdir" in result.stdout

    def test_stdout_callback(self) -> None:
        """Test stdout callback."""
        from dinbutler import Sandbox

        captured: list[str] = []

        with Sandbox.create() as sandbox:
            sandbox.run_code(
                "print('callback test')",
                on_stdout=lambda x: captured.append(x),
            )

        assert len(captured) == 1
        assert "callback test" in captured[0]


@skip_without_docker
class TestAsyncSandbox:
    """Tests for the AsyncSandbox class."""

    @pytest.mark.asyncio
    async def test_async_create(self) -> None:
        """Test creating an async sandbox."""
        from dinbutler import AsyncSandbox

        async with await AsyncSandbox.create() as sandbox:
            assert sandbox.sandbox_id is not None

    @pytest.mark.asyncio
    async def test_async_run_code(self) -> None:
        """Test running code asynchronously."""
        from dinbutler import AsyncSandbox

        async with await AsyncSandbox.create() as sandbox:
            result = await sandbox.run_code("print('Hello, async!')")
            assert result.text == "Hello, async!"
            assert result.error is None
