"""Unit tests for the create_capture use case."""

import pytest

from app.adapter.output.mock_capture_repository import MockCaptureRepository
from app.adapter.output.mock_media_storage import MockMediaStorage
from app.application.create_capture import CreateCaptureRequest, CreateCaptureUsecase
from app.domain.models.capture import CaptureKind, UnsupportedMediaTypeError


@pytest.fixture
def capture_repository() -> MockCaptureRepository:
    """Mock repository recording captures in memory."""
    return MockCaptureRepository()


@pytest.fixture
def media_storage() -> MockMediaStorage:
    """Mock storage recording file bytes in memory."""
    return MockMediaStorage()


@pytest.fixture
def usecase(
    capture_repository: MockCaptureRepository, media_storage: MockMediaStorage
) -> CreateCaptureUsecase:
    """Use case under test, wired to the in-memory mocks."""
    return CreateCaptureUsecase(
        media_storage=media_storage, capture_repository=capture_repository
    )


def _request(content_type: str, filename: str = "note.bin") -> CreateCaptureRequest:
    return CreateCaptureRequest(
        household_id="hh-1",
        member_id="mem-1",
        content=b"payload",
        filename=filename,
        content_type=content_type,
    )


async def test_create_capture_should_persist_photo_capture_when_image_uploaded(
    usecase: CreateCaptureUsecase,
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
) -> None:
    capture = await usecase(_request("image/jpeg", filename="receipt.jpg"))

    assert capture.kind is CaptureKind.PHOTO
    assert capture_repository.captures == [capture]
    assert media_storage.stored[capture.media_path] == b"payload"


async def test_create_capture_should_persist_audio_capture_when_audio_uploaded(
    usecase: CreateCaptureUsecase, capture_repository: MockCaptureRepository
) -> None:
    capture = await usecase(_request("audio/m4a", filename="note.m4a"))

    assert capture.kind is CaptureKind.AUDIO
    assert capture_repository.captures == [capture]


async def test_create_capture_should_raise_error_when_content_type_unsupported(
    usecase: CreateCaptureUsecase, capture_repository: MockCaptureRepository
) -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        await usecase(_request("text/plain"))

    assert capture_repository.captures == []


def test_create_capture_request_should_raise_error_when_household_id_blank() -> None:
    with pytest.raises(ValueError, match="household_id"):
        CreateCaptureRequest(
            household_id="  ",
            member_id="mem-1",
            content=b"payload",
            filename="receipt.jpg",
            content_type="image/jpeg",
        )


def test_create_capture_request_should_raise_error_when_content_empty() -> None:
    with pytest.raises(ValueError, match="content"):
        CreateCaptureRequest(
            household_id="hh-1",
            member_id="mem-1",
            content=b"",
            filename="receipt.jpg",
            content_type="image/jpeg",
        )
