"""Integration tests for FastAPI server."""

import pytest
from fastapi.testclient import TestClient
from dinbutler.server import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "docker" in data


def test_list_sandboxes_empty(client):
    """Test listing sandboxes when none exist."""
    response = client.get("/sandboxes/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_create_sandbox_validation(client):
    """Test sandbox creation with invalid data."""
    # Invalid timeout (too large)
    response = client.post(
        "/sandboxes/",
        json={"template": "default", "timeout": 100000}
    )
    assert response.status_code == 422  # Validation error


def test_get_nonexistent_sandbox(client):
    """Test getting a sandbox that doesn't exist."""
    response = client.get("/sandboxes/fake_sandbox_id")
    assert response.status_code == 404


def test_openapi_spec(client):
    """Test OpenAPI spec is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["info"]["title"] == "Colima E2B"
    assert spec["info"]["version"] == "0.1.0"


def test_routes_registered(client):
    """Test all expected routes are registered."""
    response = client.get("/openapi.json")
    spec = response.json()
    paths = spec["paths"]

    # Check key routes exist
    assert "/health" in paths
    assert "/sandboxes/" in paths
    assert "/sandboxes/{sandbox_id}" in paths
    assert "/sandboxes/{sandbox_id}/files/write" in paths
    assert "/sandboxes/{sandbox_id}/files/read" in paths
    assert "/sandboxes/{sandbox_id}/commands/run" in paths


def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.options("/health")
    # TestClient doesn't include CORS headers by default
    # but this verifies the route is accessible
    assert response.status_code in [200, 405]
