"""Pytest configuration and fixtures."""

import pytest
import logging

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


@pytest.fixture(scope="session")
def docker_available():
    """Check if Docker is available."""
    from dinbutler.services.docker_client import get_docker_client

    try:
        client = get_docker_client()
        return client.ping()
    except Exception:
        return False


@pytest.fixture(autouse=True)
def skip_if_no_docker(request, docker_available):
    """Skip tests if Docker is not available."""
    if not docker_available:
        pytest.skip("Docker not available")


@pytest.fixture
def sandbox():
    """Create a sandbox for testing."""
    from dinbutler import Sandbox

    sandbox = Sandbox.create(timeout=120)
    yield sandbox

    try:
        sandbox.kill()
    except Exception:
        pass


@pytest.fixture
async def async_sandbox():
    """Create an async sandbox for testing."""
    from dinbutler import AsyncSandbox

    sandbox = await AsyncSandbox.create(timeout=120)
    yield sandbox

    try:
        await sandbox.kill()
    except Exception:
        pass
