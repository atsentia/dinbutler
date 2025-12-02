# Colima E2B Integration Tests

This directory contains comprehensive integration tests for the colima-e2b package.

## Test Structure

```
tests/
├── __init__.py              # Tests package initialization
├── conftest.py              # Pytest configuration and fixtures
├── test_sandbox.py          # Main Sandbox class tests
├── test_async_sandbox.py    # AsyncSandbox tests
├── test_services.py         # Service layer unit tests
└── README.md               # This file
```

## Prerequisites

1. **Docker must be running** - The tests use Docker to create sandboxes
2. **Install test dependencies**:
   ```bash
   pip install pytest pytest-asyncio
   ```

3. **Install the package**:
   ```bash
   pip install -e .
   ```

## Running Tests

### Run all tests
```bash
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_sandbox.py -v
pytest tests/test_async_sandbox.py -v
pytest tests/test_services.py -v
```

### Run specific test class
```bash
pytest tests/test_sandbox.py::TestSandboxLifecycle -v
pytest tests/test_sandbox.py::TestSandboxCommands -v
pytest tests/test_sandbox.py::TestSandboxFilesystem -v
pytest tests/test_sandbox.py::TestSandboxPty -v
```

### Run specific test
```bash
pytest tests/test_sandbox.py::TestSandboxLifecycle::test_create_sandbox -v
```

### Run with output capture disabled (see print statements)
```bash
pytest tests/ -v -s
```

### Run with debugging
```bash
pytest tests/ -v --pdb
```

### Run async tests only
```bash
pytest tests/test_async_sandbox.py -v
```

## Test Coverage

### Test Files Overview

#### test_sandbox.py
- **TestSandboxLifecycle**: Sandbox creation, connection, listing, context managers
- **TestSandboxCommands**: Command execution, processes, environment variables
- **TestSandboxFilesystem**: File operations, directory listing, file metadata
- **TestSandboxPty**: PTY creation and interaction

#### test_async_sandbox.py
- **TestAsyncSandboxLifecycle**: Async sandbox lifecycle operations
- **TestAsyncCommands**: Async command execution
- **TestAsyncFilesystem**: Async file operations

#### test_services.py
- **TestDockerClient**: Docker client singleton and connectivity
- **TestSandboxManager**: Low-level sandbox management
- **TestFilesystemService**: Direct filesystem service tests
- **TestCommandsService**: Direct command service tests

### Coverage by Feature

| Feature | Test Count | Location |
|---------|------------|----------|
| Sandbox lifecycle | 7 | test_sandbox.py::TestSandboxLifecycle |
| Command execution | 6 | test_sandbox.py::TestSandboxCommands |
| Filesystem ops | 8 | test_sandbox.py::TestSandboxFilesystem |
| PTY sessions | 2 | test_sandbox.py::TestSandboxPty |
| Async operations | 4 | test_async_sandbox.py |
| Service layer | 6 | test_services.py |
| **Total** | **33** | |

## Fixtures

The tests use several pytest fixtures defined in `conftest.py`:

- **docker_available**: Checks if Docker is running (session-scoped)
- **skip_if_no_docker**: Automatically skips tests if Docker is unavailable
- **sandbox**: Creates a test sandbox (function-scoped, auto-cleanup)
- **async_sandbox**: Creates an async test sandbox (function-scoped, auto-cleanup)

## Expected Behavior

### Successful Test Run
```bash
$ pytest tests/ -v
======================== test session starts ========================
tests/test_sandbox.py::TestSandboxLifecycle::test_create_sandbox PASSED
tests/test_sandbox.py::TestSandboxLifecycle::test_create_sandbox_with_context_manager PASSED
...
======================== 33 passed in 45.23s ========================
```

### Docker Not Available
```bash
$ pytest tests/ -v
======================== test session starts ========================
tests/test_sandbox.py::TestSandboxLifecycle::test_create_sandbox SKIPPED (Docker not available)
...
======================== 33 skipped in 0.12s ========================
```

## Troubleshooting

### Tests fail with "Docker not available"
- Ensure Docker/Colima is running:
  ```bash
  docker ps
  ```
- Start Docker/Colima:
  ```bash
  colima start
  ```

### Tests timeout
- Sandboxes have a default 120-second timeout in fixtures
- Individual tests use 60-second timeouts
- Increase if needed in `conftest.py` or test files

### Cleanup issues
- Tests use context managers and fixtures for automatic cleanup
- Manual cleanup if needed:
  ```bash
  docker ps -a | grep sandbox- | awk '{print $1}' | xargs docker rm -f
  ```

### Import errors
- Ensure package is installed:
  ```bash
  pip install -e .
  ```
- Check PYTHONPATH includes project root

## Writing New Tests

### Test Template
```python
def test_my_feature(self):
    """Test description."""
    with Sandbox.create() as sandbox:
        # Test code here
        result = sandbox.commands.run("echo test")
        assert "test" in result.stdout
```

### Async Test Template
```python
@pytest.mark.asyncio
async def test_my_async_feature(self):
    """Test description."""
    async with await AsyncSandbox.create() as sandbox:
        # Test code here
        result = await sandbox.commands.run("echo async")
        assert "async" in result.stdout
```

### Using Fixtures
```python
def test_with_fixture(self, sandbox):
    """Test using the sandbox fixture."""
    # Sandbox already created and will be cleaned up
    result = sandbox.commands.run("pwd")
    assert result.exit_code == 0
```

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio

      - name: Run tests
        run: pytest tests/ -v
```

## Test Maintenance

- **Keep tests isolated**: Each test should be independent
- **Use fixtures**: Leverage pytest fixtures for common setup
- **Clean up resources**: Always use context managers or fixtures
- **Assert meaningfully**: Make assertions specific and descriptive
- **Document edge cases**: Comment on non-obvious test scenarios

## Contributing

When adding new features to colima-e2b:

1. Write tests first (TDD approach)
2. Ensure all existing tests pass
3. Add tests for new functionality
4. Update this README if new test files are added
5. Run full test suite before submitting PR

## Performance Considerations

- Tests create real Docker containers (takes time)
- Average test run: ~45-60 seconds for full suite
- Use `-k` flag to run subset during development:
  ```bash
  pytest tests/ -k "test_create_sandbox" -v
  ```

## License

Same as colima-e2b package (MIT License)
