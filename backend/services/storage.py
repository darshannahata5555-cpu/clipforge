import os
import aiofiles
import boto3
from config import settings


class LocalStorage:
    def __init__(self, base_path: str):
        self.base = base_path

    async def save(self, key: str, data: bytes) -> str:
        path = os.path.join(self.base, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return key

    def save_sync(self, key: str, data: bytes) -> str:
        path = os.path.join(self.base, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return key

    def local_path(self, key: str) -> str:
        return os.path.join(self.base, key)

    def public_url(self, key: str) -> str:
        # Served by FastAPI /storage static mount in dev
        return f"/storage/{key}"

    def delete(self, key: str):
        path = os.path.join(self.base, key)
        if os.path.exists(path):
            os.remove(path)


class R2Storage:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )
        self.bucket = settings.r2_bucket
        self.public_url_base = settings.r2_public_url.rstrip("/")

    async def save(self, key: str, data: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key

    def save_sync(self, key: str, data: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key

    def local_path(self, key: str) -> str:
        # R2 doesn't have local paths; caller must download first
        raise RuntimeError("R2Storage has no local_path. Use download_to_tmp().")

    def download_to_tmp(self, key: str, tmp_path: str) -> str:
        self.client.download_file(self.bucket, key, tmp_path)
        return tmp_path

    def upload_file(self, key: str, file_path: str) -> str:
        with open(file_path, "rb") as f:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=f)
        return key

    def public_url(self, key: str) -> str:
        return f"{self.public_url_base}/{key}"

    def delete(self, key: str):
        self.client.delete_object(Bucket=self.bucket, Key=key)


def _make_storage():
    if settings.storage_type == "r2":
        return R2Storage()
    return LocalStorage(settings.local_storage_path)


storage = _make_storage()
