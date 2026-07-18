"""Capture entity: an uploaded photo or voice note awaiting extraction."""

from datetime import datetime
from enum import StrEnum

from attrs import define


class CaptureKind(StrEnum):
    """Medium of a capture, derived from the uploaded file's MIME type."""

    PHOTO = "photo"
    AUDIO = "audio"

    @classmethod
    def from_content_type(cls, content_type: str) -> "CaptureKind":
        """Derive the capture kind from a MIME content type.

        :param content_type: MIME type of the uploaded file.
        :return: ``PHOTO`` for ``image/*`` types, ``AUDIO`` for ``audio/*`` types.
        :raises UnsupportedMediaTypeError: When the type is neither image nor audio.
        """
        if content_type.startswith("image/"):
            return cls.PHOTO
        if content_type.startswith("audio/"):
            return cls.AUDIO
        raise UnsupportedMediaTypeError(content_type)


class UnsupportedMediaTypeError(ValueError):
    """Raised when an uploaded file is neither an image nor an audio recording."""


@define(frozen=True)
class Capture:
    """An uploaded photo or voice note, stored and awaiting extraction.

    :param id: Unique identifier of the capture.
    :param household_id: Household the capture belongs to.
    :param member_id: Member who submitted the capture.
    :param kind: Whether the capture is a photo or an audio note.
    :param media_path: Storage-relative path of the stored media file.
    :param created_at: When the capture was created (UTC).
    """

    id: str
    household_id: str
    member_id: str
    kind: CaptureKind
    media_path: str
    created_at: datetime
