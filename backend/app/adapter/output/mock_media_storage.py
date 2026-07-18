"""In-memory mock of the media storage port for tests."""

from attrs import define, field

from app.domain.ports.media_storage import MediaStoragePort, MediaStoreRequest


@define
class MockMediaStorage(MediaStoragePort):
    """Media storage keeping file bytes in an in-memory mapping."""

    stored: dict[str, bytes] = field(factory=dict)

    async def store(self, request: MediaStoreRequest) -> str:
        """Record the file content in memory.

        :param request: The file content and naming metadata to store.
        :return: A synthetic storage path unique within this instance.
        """
        name = f"{len(self.stored)}-{request.filename}"
        self.stored[name] = request.content
        return name
