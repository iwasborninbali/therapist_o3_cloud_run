import pytest


def test_health_endpoint(client):
    """Test that the health endpoint returns a 200 OK response with status 'ok'"""
    response = client.get("/health")

    # Check that the response status code is 200 (OK)
    assert response.status_code == 200

    # Check that the response JSON contains the correct status
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
