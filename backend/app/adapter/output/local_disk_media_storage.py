"""Local-disk implementation of the media storage port."""

import asyncio
from pathlib import Path
from uuid import uuid4

from attrs import define

from app.domain.ports.media_storage import MediaStoragePort, MediaStoreRequest


@define(kw_only=True)
class LocalDiskMediaStorage(MediaStoragePort):
    """Media storage writing files into a directory on the local disk."""

    root_dir: Path

    async def store(self, request: MediaStoreRequest) -> str:
        """Write the file under the root directory with a collision-free name.

        :param request: The file content and naming metadata to store.
        :return: The stored file's name, relative to the root directory.
        :raises OSError: When the directory or file cannot be written.
        """
        # Only the extension of the client filename is kept; the basename is a
        # fresh uuid, which both avoids collisions and neutralizes path traversal.
        name = f"{uuid4().hex}{Path(request.filename).suffix}"
        await asyncio.to_thread(self._write, self.root_dir / name, request.content)
        return name

    @staticmethod
    def _write(target: Path, content: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
