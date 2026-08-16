from __future__ import annotations

import json
import tarfile
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from forge.contracts.models import ArtifactRef, GPUJobRequest
from forge.integrations.r2.store import InMemoryObjectStore
from forge.integrations.runpod.handler import ProcessorOutput, RunPodHandler
from forge.modules.packaging.delivery import DeliveryBuilder, DeliveryEpisode, DeliveryRequest
from tests.helpers import SHA, accepted_quality
from workers.processors import DeliveryPackageProcessor


class MissingObjectError(Exception):
    response = {
        "Error": {"Code": "NoSuchKey"},
        "ResponseMetadata": {"HTTPStatusCode": 404},
    }


class MissingObjectClient:
    def get_object(self, **kwargs):
        raise MissingObjectError()


class EchoProcessor:
    def __init__(self):
        self.calls = 0

    def process(self, inputs, config, request):
        self.calls += 1
        return (ProcessorOutput("echo", "echo.json", config + inputs["source"]),)


class StorageRunPodPackagingTest(unittest.TestCase):
    def test_runpod_package_stage_emits_archive_and_manifest(self) -> None:
        store = InMemoryObjectStore()
        source = store.put_bytes(
            "r2://forge-dev/results/trajectory.npz",
            b"trajectory",
            "application/octet-stream",
        )
        config = {
            "schema_version": "forge.package-job.v1",
            "order_id": "ord_1",
            "tenant_id": "ten_1",
            "dataset_version": "v1",
            "rights_profile": "customer_exclusive_derivatives",
            "quality_decision": {"route": "ACCEPT"},
            "artifacts": [
                {
                    "input_kind": "artifact_00000",
                    "kind": "robot_trajectory",
                    "filename": "trajectory.npz",
                    "uri": source.uri,
                    "sha256": source.sha256,
                }
            ],
        }
        config_object = store.put_bytes(
            "r2://forge-dev/config/package.json",
            json.dumps(config).encode(),
            "application/json",
        )
        request = GPUJobRequest(
            job_id="job_package",
            idempotency_key=SHA,
            stage="package",
            input_artifacts=(ArtifactRef("artifact_00000", source.uri, source.sha256),),
            config_uri=config_object.uri,
            container_image="ghcr.io/forge/worker@sha256:" + SHA,
            pipeline_version="v1",
            output_prefix="r2://forge-dev/delivery/ord_1",
        )
        result = RunPodHandler(
            store, {"package": DeliveryPackageProcessor()}, "development"
        ).handle(request)
        self.assertEqual(result.status, "succeeded")
        archive_ref = next(item for item in result.artifacts if item.kind == "delivery_package")
        with tarfile.open(
            fileobj=BytesIO(store.get_bytes(archive_ref.uri)), mode="r:gz"
        ) as archive:
            self.assertIn("manifest.json", archive.getnames())
            self.assertIn("artifacts/trajectory.npz", archive.getnames())

    def test_r2_missing_object_is_mapped_to_file_not_found(self) -> None:
        from forge.integrations.r2.store import R2ObjectStore

        store = R2ObjectStore(MissingObjectClient(), "forge-dev")
        with self.assertRaises(FileNotFoundError):
            store.get_bytes("r2://forge-dev/missing.json")

    def test_runpod_handler_verifies_checksum_and_is_idempotent(self) -> None:
        store = InMemoryObjectStore()
        source = store.put_bytes(
            "r2://forge-dev/input/source.bin", b"source", "application/octet-stream"
        )
        store.put_bytes("r2://forge-dev/config/job.json", b"config", "application/json")
        request = GPUJobRequest(
            job_id="job_1",
            idempotency_key=SHA,
            stage="reconstruction",
            input_artifacts=(ArtifactRef("source", source.uri, source.sha256),),
            config_uri="r2://forge-dev/config/job.json",
            container_image="ghcr.io/forge/reconstruction@sha256:" + SHA,
            pipeline_version="v1",
            output_prefix="r2://forge-dev/output/job_1",
        )
        processor = EchoProcessor()
        handler = RunPodHandler(store, {"reconstruction": processor}, "development")
        first = handler.handle(request)
        second = RunPodHandler(store, {"reconstruction": processor}, "development").handle(request)
        self.assertEqual(first, second)
        self.assertEqual(processor.calls, 1)
        self.assertEqual(first.status, "succeeded")
        self.assertTrue(first.simulation)

    def test_delivery_writes_lineage_and_checksums(self) -> None:
        quality = accepted_quality("ep_1")
        episode = DeliveryEpisode(
            episode_id="ep_1",
            source_demonstration_id="demo_1",
            motion_family="manipulation",
            robot_id="robot_1",
            trajectory_uri="r2://forge-dev/episodes/ep_1.npz",
            trajectory_sha256=SHA,
            quality=quality,
        )
        request = DeliveryRequest(
            order_id="ord_1",
            tenant_id="tenant_1",
            rights_profile="customer_exclusive_derivatives",
            customer_license_text="Customer owns the listed derivative episode artifacts.",
            skill_ir_artifacts=({"uri": "r2://forge-dev/skill.json", "sha256": SHA},),
            episodes=(episode,),
            model_versions={"forge": "0.1.0"},
            production=False,
        )
        with TemporaryDirectory() as directory:
            target = DeliveryBuilder().build(request, Path(directory))
            manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["episodes"][0]["episode_id"], "ep_1")
            self.assertTrue((target / "provenance" / "artifact_checksums.sha256").exists())


if __name__ == "__main__":
    unittest.main()
