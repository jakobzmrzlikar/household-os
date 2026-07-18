"""Driven port for persisting uploaded media binaries."""

from typing import Protocol, runtime_checkable

from attrs import define


@runtime_checkable
class MediaStoragePort(Protocol):
    """Port for storing uploaded media files (receipt photos, voice notes)."""

    async def store(self, request: "MediaStoreRequest") -> str:
        """Persist a media file.

        :param request: The file content and naming metadata to store.
        :return: A storage-relative path identifying the stored file.
        :raises OSError: When the backing storage cannot be written.
        """
        ...


@define
class MediaStoreRequest:
    """A media file to persist.

    :param content: Raw file bytes.
    :param filename: Original client filename; its extension is preserved.
    :param content_type: MIME type of the file.
    """

    content: bytes
    filename: str
    content_type: str
