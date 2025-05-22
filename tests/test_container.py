"""Tests for Docker container functionality."""

import os
import time
import pytest
import requests
import docker

# Skip tests if SKIP_CONTAINER_TESTS is set
pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_CONTAINER_TESTS") == "True",
    reason="Skip container tests via environment variable"
)

# Container configuration
CONTAINER_NAME = "telegram-bot-test"
IMAGE_NAME = "telegram-bot:test"
HOST_PORT = 8081
CONTAINER_PORT = 8080


@pytest.fixture(scope="module")
def docker_client():
    """Create a Docker client for building and running containers."""
    return docker.from_env()


@pytest.fixture(scope="module")
def build_test_image(docker_client):
    """Build the Docker image for testing."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print(f"Building Docker image {IMAGE_NAME}...")
    docker_client.images.build(
        path=project_root,
        tag=IMAGE_NAME,
        rm=True,
    )

    yield IMAGE_NAME

    try:
        docker_client.images.remove(IMAGE_NAME, force=True)
        print(f"Removed Docker image {IMAGE_NAME}")
    except docker.errors.APIError as e:
        print(f"Could not remove Docker image: {str(e)}")


@pytest.fixture(scope="module")
def start_container(docker_client, build_test_image):
    """Start a container of the test image."""
    environment = {
        "TESTING": "True",
        "TELEGRAM_TOKEN": "test_token",
        "OPENAI_API_KEY": "test_key",
        "FIREBASE_PROJECT_ID": "test_project",
        "PORT": str(CONTAINER_PORT)
    }

    print(f"Starting Docker container {CONTAINER_NAME}...")
    container = docker_client.containers.run(
        IMAGE_NAME,
        name=CONTAINER_NAME,
        detach=True,
        environment=environment,
        ports={f"{CONTAINER_PORT}/tcp": HOST_PORT},
        remove=True
    )

    print("Waiting for container to start...")
    time.sleep(5)

    container.reload()
    assert container.status == "running"

    yield container

    try:
        container.stop(timeout=1)
        print(f"Stopped Docker container {CONTAINER_NAME}")
    except docker.errors.APIError as e:
        print(f"Could not stop Docker container: {str(e)}")


def test_container_health_endpoint(start_container):
    """Test the health endpoint in the container."""
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.get(
                f"http://localhost:{HOST_PORT}/health",
                timeout=5
            )
            response.raise_for_status()

            data = response.json()
            assert "status" in data
            assert data["status"] == "ok"
            return
        except (requests.RequestException, AssertionError) as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                time.sleep(retry_delay)
            else:
                raise


def test_container_webhook_endpoint(start_container):
    """Test the webhook endpoint in the container."""
    telegram_update = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 12345,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "chat": {
                "id": 12345,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": 1612345678,
            "text": "hello"
        }
    }

    response = requests.post(
        f"http://localhost:{HOST_PORT}/webhook",
        json=telegram_update,
        timeout=5
    )

    assert response.status_code == 200
