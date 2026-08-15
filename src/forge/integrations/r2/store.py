from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Protocol
import hashlib
import os


@dataclass(frozen=True)
class StoredObject:
    uri: str
    sha256: str
    size_bytes: int
    media_type: str


class ObjectStore(Protocol):
    def put_bytes(self, uri: str, data: bytes, media_type: str) -> StoredObject: ...

    def get_bytes(self, uri: str, expected_sha256: str | None = None) -> bytes: ...


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_r2_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("r2://"):
        raise ValueError("R2 URI must start with r2://")
    bucket_and_key = uri[5:]
    bucket, separator, key = bucket_and_key.partition("/")
    if not separator or not bucket or not key or key.startswith("/"):
        raise ValueError("R2 URI must include bucket and object key")
    if ".." in key.split("/"):
        raise ValueError("R2 URI cannot contain parent traversal")
    return bucket, key


class InMemoryObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_bytes(self, uri: str, data: bytes, media_type: str) -> StoredObject:
        parse_r2_uri(uri)
        self.objects[uri] = (bytes(data), media_type)
        return StoredObject(uri, _sha256(data), len(data), media_type)

    def get_bytes(self, uri: str, expected_sha256: str | None = None) -> bytes:
        try:
            data = self.objects[uri][0]
        except KeyError as error:
            raise FileNotFoundError(uri) from error
        actual = _sha256(data)
        if expected_sha256 and actual != expected_sha256:
            raise ValueError("OBJECT_CHECKSUM_MISMATCH")
        return data


class R2ObjectStore:
    """S3-compatible R2 adapter; boto3 is an optional cloud dependency."""

    def __init__(self, client: object, bucket_name: str) -> None:
        self.client = client
        self.bucket_name = bucket_name

    @classmethod
    def from_env(cls) -> "R2ObjectStore":
        required = (
            "R2_BUCKET_NAME",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_ENDPOINT",
        )
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise RuntimeError(f"R2_CONFIGURATION_MISSING:{','.join(missing)}")
        try:
            import boto3  # type: ignore[import-not-found]
        except ImportError as error:
            raise RuntimeError("INSTALL_FORGE_CLOUD_EXTRA") from error
        client = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT"],
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )
        return cls(client, os.environ["R2_BUCKET_NAME"])

    def put_bytes(self, uri: str, data: bytes, media_type: str) -> StoredObject:
        bucket, key = parse_r2_uri(uri)
        self._assert_bucket(bucket)
        self.client.put_object(  # type: ignore[attr-defined]
            Bucket=bucket,
            Key=key,
            Body=BytesIO(data),
            ContentType=media_type,
            Metadata={"sha256": _sha256(data)},
        )
        return StoredObject(uri, _sha256(data), len(data), media_type)

    def get_bytes(self, uri: str, expected_sha256: str | None = None) -> bytes:
        bucket, key = parse_r2_uri(uri)
        self._assert_bucket(bucket)
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)  # type: ignore[attr-defined]
        except Exception as error:
            response_data = getattr(error, "response", {})
            error_code = str(response_data.get("Error", {}).get("Code", ""))
            status_code = response_data.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if error_code in {"NoSuchKey", "NotFound", "404"} or status_code == 404:
                raise FileNotFoundError(uri) from error
            raise
        data = response["Body"].read()
        actual = _sha256(data)
        if expected_sha256 and actual != expected_sha256:
            raise ValueError("OBJECT_CHECKSUM_MISMATCH")
        return data

    def _assert_bucket(self, bucket: str) -> None:
        if bucket != self.bucket_name:
            raise PermissionError("R2_BUCKET_OUTSIDE_CONFIGURED_SCOPE")
