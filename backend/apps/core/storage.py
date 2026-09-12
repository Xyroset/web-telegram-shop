import hashlib
import os
from typing import cast

from boto3.s3.transfer import TransferConfig
from django.core.files.base import File
from django.core.files.storage import Storage, storages
from django.utils.functional import LazyObject


class HashedStorage(storages["default"].__class__):  # type: ignore[misc]
    """
    Content-Addressable Storage (CAS) for de-duplicating uploaded files.
    Files with the same content hash will reuse the existing S3 object.
    """

    @property
    def transfer_config(self) -> TransferConfig:
        return TransferConfig(
            multipart_threshold=15 * 1024 * 1024,
            multipart_chunksize=15 * 1024 * 1024,
            use_threads=False,
        )

    def _get_available_name(self, name: str, max_length: int | None = None) -> str:
        if self.exists(name):
            return name
        return str(super()._get_available_name(name, max_length=max_length))

    def save(self, name: str, content: File, max_length: int | None = None) -> str:
        hasher = hashlib.md5()
        for chunk in content.chunks():
            hasher.update(chunk)

        content.seek(0)

        hash_hex = hasher.hexdigest()
        dir_name, file_name = os.path.split(name)
        ext = os.path.splitext(file_name)[1].lower()

        hashed_name = f"{dir_name}/{hash_hex}{ext}" if dir_name else f"{hash_hex}{ext}"

        if self.exists(hashed_name):
            return hashed_name

        return str(super().save(hashed_name, content, max_length))


class LazyHashedStorage(LazyObject):
    def _setup(self) -> None:
        self._wrapped = HashedStorage()


hashed_storage = cast(Storage, LazyHashedStorage())
