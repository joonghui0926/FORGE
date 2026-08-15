from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from forge.integrations.r2.store import R2ObjectStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload and verify a FORGE artifact in R2")
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--media-type", default="application/octet-stream")
    args = parser.parse_args()
    if args.file.is_symlink() or not args.file.is_file():
        raise FileNotFoundError(args.file)
    if args.key.startswith("/") or ".." in args.key.split("/"):
        raise ValueError("R2_KEY_INVALID")
    bucket = os.environ.get("R2_BUCKET_NAME", "")
    if not bucket:
        raise RuntimeError("R2_CONFIGURATION_MISSING:R2_BUCKET_NAME")
    data = args.file.read_bytes()
    uri = f"r2://{bucket}/{args.key}"
    store = R2ObjectStore.from_env()
    stored = store.put_bytes(uri, data, args.media_type)
    if store.get_bytes(uri, stored.sha256) != data:
        raise RuntimeError("R2_ROUND_TRIP_MISMATCH")
    print(
        json.dumps(
            {
                "uri": stored.uri,
                "sha256": stored.sha256,
                "size_bytes": stored.size_bytes,
                "media_type": stored.media_type,
                "round_trip_verified": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
