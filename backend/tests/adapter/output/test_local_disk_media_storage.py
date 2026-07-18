"""Unit tests for the local-disk media storage adapter."""

from pathlib import Path

from app.adapter.output.local_disk_media_storage import LocalDiskMediaStorage
from app.domain.ports.media_storage import MediaStoreRequest


async def test_local_disk_media_storage_should_write_file_when_storing(
    tmp_path: Path,
) -> None:
    storage = LocalDiskMediaStorage(root_dir=tmp_path / "uploads")

    name = await storage.store(
        MediaStoreRequest(content=b"data", filename="a.jpg", content_type="image/jpeg")
    )

    assert (tmp_path / "uploads" / name).read_bytes() == b"data"
    assert name.endswith(".jpg")


async def test_local_disk_media_storage_should_use_unique_names_when_filenames_collide(
    tmp_path: Path,
) -> None:
    storage = LocalDiskMediaStorage(root_dir=tmp_path)
    request = MediaStoreRequest(
        content=b"data", filename="a.jpg", content_type="image/jpeg"
    )

    first = await storage.store(request)
    second = await storage.store(request)

    assert first != second
