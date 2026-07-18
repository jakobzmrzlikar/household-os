"""Endpoint tests for the create_capture command."""

import pytest
from fastapi.testclient import TestClient

from app.adapter.output.mock_capture_repository import MockCaptureRepository
from app.adapter.output.mock_media_storage import MockMediaStorage
from app.infrastructure.app import create_app
from app.infrastructure.container import Container


@pytest.fixture
def capture_repository() -> MockCaptureRepository:
    """Mock repository recording captures in memory."""
    return MockCaptureRepository()


@pytest.fixture
def client(capture_repository: MockCaptureRepository) -> TestClient:
    """App client with storage and persistence overridden by in-memory mocks.

    Built per-test (not at module import) so this container is the most recently
    wired one when the request runs.
    """
    app = create_app()
    container: Container = app.state.container
    # dependency_injector's stubs leave Provider.override partially generic.
    container.media_storage.override(  # pyright: ignore[reportUnknownMemberType]
        MockMediaStorage()
    )
    container.capture_repository.override(  # pyright: ignore[reportUnknownMemberType]
        capture_repository
    )
    return TestClient(app)


def test_create_capture_endpoint_should_return_201_when_photo_uploaded(
    client: TestClient, capture_repository: MockCaptureRepository
) -> None:
    response = client.post(
        "/create_capture",
        data={"household_id": "hh-1", "member_id": "mem-1"},
        files={"file": ("receipt.jpg", b"fake-jpeg", "image/jpeg")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "photo"
    assert [capture.id for capture in capture_repository.captures] == [body["id"]]


def test_create_capture_endpoint_should_return_201_when_audio_uploaded(
    client: TestClient,
) -> None:
    response = client.post(
        "/create_capture",
        data={"household_id": "hh-1", "member_id": "mem-1"},
        files={"file": ("note.m4a", b"fake-m4a", "audio/m4a")},
    )

    assert response.status_code == 201
    assert response.json()["kind"] == "audio"


def test_create_capture_endpoint_should_return_415_when_file_not_media(
    client: TestClient, capture_repository: MockCaptureRepository
) -> None:
    response = client.post(
        "/create_capture",
        data={"household_id": "hh-1", "member_id": "mem-1"},
        files={"file": ("notes.txt", b"text", "text/plain")},
    )

    assert response.status_code == 415
    assert capture_repository.captures == []


def test_create_capture_endpoint_should_return_422_when_household_id_blank(
    client: TestClient,
) -> None:
    response = client.post(
        "/create_capture",
        data={"household_id": "   ", "member_id": "mem-1"},
        files={"file": ("receipt.jpg", b"fake-jpeg", "image/jpeg")},
    )

    assert response.status_code == 422
