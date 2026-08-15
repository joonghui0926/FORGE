from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
import json
import os
import tempfile

from forge.contracts.models import QualityResult, SCHEMA_VERSIONS, canonical_json


@dataclass(frozen=True)
class DeliveryEpisode:
    episode_id: str
    source_demonstration_id: str
    motion_family: str
    robot_id: str
    trajectory_uri: str
    trajectory_sha256: str
    quality: QualityResult
    parent_episode_id: str | None = None

    def __post_init__(self) -> None:
        if self.quality.subject_id != self.episode_id:
            raise ValueError("episode quality subject mismatch")
        if not self.trajectory_uri.startswith("r2://"):
            raise ValueError("delivery trajectories must be immutable R2 artifacts")


@dataclass(frozen=True)
class DeliveryRequest:
    order_id: str
    tenant_id: str
    rights_profile: str
    customer_license_text: str
    skill_ir_artifacts: tuple[dict[str, str], ...]
    episodes: tuple[DeliveryEpisode, ...]
    model_versions: dict[str, str]
    production: bool


class DeliveryBuilder:
    version = "forge-delivery-builder-v1"

    def build(self, request: DeliveryRequest, output_root: Path) -> Path:
        if not request.order_id.startswith("ord_"):
            raise ValueError("order_id must start with ord_")
        if not request.episodes:
            raise ValueError("delivery requires at least one episode")
        self._validate_episodes(request)

        target = output_root / "delivery" / request.order_id
        target.mkdir(parents=True, exist_ok=False)
        for relative in (
            "source_demonstrations/skill_ir",
            "robot_trajectories/replay_reports",
            "generated_episodes",
            "quality/evidence",
            "provenance",
            "exports/lerobot",
            "exports/rlds",
            "exports/customer_schema",
        ):
            (target / relative).mkdir(parents=True, exist_ok=True)

        manifest = {
            "schema_version": SCHEMA_VERSIONS["delivery"],
            "builder_version": self.version,
            "order_id": request.order_id,
            "tenant_id": request.tenant_id,
            "rights_profile": request.rights_profile,
            "production": request.production,
            "skill_ir_artifacts": list(request.skill_ir_artifacts),
            "episodes": [self._episode_manifest(episode) for episode in request.episodes],
            "model_versions_uri": "provenance/model_versions.json",
            "quality_aggregate_uri": "quality/aggregate.json",
            "checksum_uri": "provenance/artifact_checksums.sha256",
        }
        self._write_json(target / "manifest.json", manifest)
        self._write_json(
            target / "LICENSE_AND_RIGHTS.json",
            {
                "rights_profile": request.rights_profile,
                "customer_license_text": request.customer_license_text,
                "raw_source_rights_are_not_transferred_unless_listed": True,
            },
        )
        self._write_json(target / "provenance" / "model_versions.json", request.model_versions)
        accepted_count = sum(episode.quality.accepted for episode in request.episodes)
        self._write_json(
            target / "quality" / "aggregate.json",
            {
                "episode_count": len(request.episodes),
                "accepted_count": accepted_count,
                "acceptance_rate": accepted_count / len(request.episodes),
                "simulation_count": sum(episode.quality.simulation for episode in request.episodes),
            },
        )
        self._write_json(
            target / "quality" / "rejection_reasons.json",
            {episode.episode_id: list(episode.quality.reason_codes) for episode in request.episodes},
        )
        lineage = [
            {
                "child": episode.episode_id,
                "parent": episode.parent_episode_id or episode.source_demonstration_id,
                "trajectory_sha256": episode.trajectory_sha256,
                "quality_policy": episode.quality.policy_version,
                "quality_evidence": list(episode.quality.evidence_artifact_ids),
            }
            for episode in request.episodes
        ]
        self._write_jsonl(target / "provenance" / "graph.jsonl", lineage)
        self._write_jsonl(
            target / "raw_index.jsonl",
            [
                {
                    "source_demonstration_id": episode.source_demonstration_id,
                    "episode_id": episode.episode_id,
                    "motion_family": episode.motion_family,
                }
                for episode in request.episodes
            ],
        )
        self._write_dataset_card(target / "dataset_card.md", request)
        self._write_readme(target / "README.md", request)
        if request.production:
            self._write_parquet_index(target / "raw_index.parquet", request.episodes)
        self._write_checksums(target)
        return target

    @staticmethod
    def _validate_episodes(request: DeliveryRequest) -> None:
        ids: set[str] = set()
        for episode in request.episodes:
            if episode.episode_id in ids:
                raise ValueError("duplicate delivery episode")
            ids.add(episode.episode_id)
            if not episode.quality.accepted or episode.quality.hard_failures:
                raise PermissionError("DELIVERY_CONTAINS_UNACCEPTED_EPISODE")
            if episode.quality.replay is None or not episode.quality.replay.replay_success:
                raise PermissionError("DELIVERY_REQUIRES_REPLAY")
            if request.production and episode.quality.simulation:
                raise PermissionError("PRODUCTION_DELIVERY_CONTAINS_SIMULATION")

    @staticmethod
    def _episode_manifest(episode: DeliveryEpisode) -> dict[str, Any]:
        return {
            "episode_id": episode.episode_id,
            "source_demonstration_id": episode.source_demonstration_id,
            "parent_episode_id": episode.parent_episode_id,
            "motion_family": episode.motion_family,
            "robot_id": episode.robot_id,
            "trajectory": {
                "uri": episode.trajectory_uri,
                "sha256": episode.trajectory_sha256,
            },
            "quality": episode.quality.to_dict(),
        }

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        DeliveryBuilder._atomic_write(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")

    @staticmethod
    def _write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
        DeliveryBuilder._atomic_write(path, "".join(canonical_json(value) + "\n" for value in values))

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise

    @staticmethod
    def _write_dataset_card(path: Path, request: DeliveryRequest) -> None:
        families = sorted({episode.motion_family for episode in request.episodes})
        content = (
            f"# Dataset card: {request.order_id}\n\n"
            f"Validated robot-ready episodes: {len(request.episodes)}.\n\n"
            f"Motion families: {', '.join(families)}.\n\n"
            "Every episode passed its declared motion-specific physics replay profile. "
            "See `manifest.json` and `quality/` for thresholds, evidence, and lineage.\n"
        )
        DeliveryBuilder._atomic_write(path, content)

    @staticmethod
    def _write_readme(path: Path, request: DeliveryRequest) -> None:
        DeliveryBuilder._atomic_write(
            path,
            f"# FORGE delivery {request.order_id}\n\n"
            "Start with `manifest.json`. Verify `provenance/artifact_checksums.sha256` "
            "before loading trajectory artifacts. Generated episodes are included only after "
            "independent replay validation.\n",
        )

    @staticmethod
    def _write_parquet_index(path: Path, episodes: tuple[DeliveryEpisode, ...]) -> None:
        try:
            import pyarrow as pa  # type: ignore[import-not-found]
            import pyarrow.parquet as pq  # type: ignore[import-not-found]
        except ImportError as error:
            raise RuntimeError("INSTALL_FORGE_DATA_EXTRA_FOR_PRODUCTION_DELIVERY") from error
        table = pa.Table.from_pylist(
            [
                {
                    "source_demonstration_id": episode.source_demonstration_id,
                    "episode_id": episode.episode_id,
                    "motion_family": episode.motion_family,
                    "robot_id": episode.robot_id,
                    "trajectory_uri": episode.trajectory_uri,
                    "trajectory_sha256": episode.trajectory_sha256,
                }
                for episode in episodes
            ]
        )
        pq.write_table(table, path)

    @staticmethod
    def _write_checksums(target: Path) -> None:
        checksum_path = target / "provenance" / "artifact_checksums.sha256"
        lines: list[str] = []
        for path in sorted(item for item in target.rglob("*") if item.is_file()):
            if path == checksum_path:
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(target).as_posix()}\n")
        DeliveryBuilder._atomic_write(checksum_path, "".join(lines))
