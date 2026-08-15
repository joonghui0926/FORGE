from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime

from forge.integrations.r2.store import R2ObjectStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Write and verify a bounded FORGE R2 sentinel")
    parser.add_argument("--name", default="codex-live-check")
    args = parser.parse_args()
    captured_at = datetime.now(UTC).isoformat()
    payload = (
        json.dumps(
            {
                "schema_version": "forge.r2-connectivity.v1",
                "captured_at": captured_at,
                "name": args.name,
                "contains_customer_data": False,
            },
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    bucket = os.environ.get("R2_BUCKET_NAME", "")
    if not bucket:
        raise RuntimeError("R2_CONFIGURATION_MISSING:R2_BUCKET_NAME")
    key_timestamp = captured_at.replace(":", "-").replace("+", "_")
    uri = f"r2://{bucket}/_forge/connectivity/{key_timestamp}.json"
    store = R2ObjectStore.from_env()
    stored = store.put_bytes(uri, payload, "application/json")
    restored = store.get_bytes(uri, stored.sha256)
    if restored != payload:
        raise RuntimeError("R2_ROUND_TRIP_MISMATCH")
    print(
        json.dumps(
            {
                "uri": stored.uri,
                "sha256": stored.sha256,
                "size_bytes": stored.size_bytes,
                "round_trip_verified": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
