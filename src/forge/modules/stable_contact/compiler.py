from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from math import sqrt

from forge.geometry import Pose, Vec3, distance, dot, normalize
from forge.modules.skill_ir.models import ContactAnchor


@dataclass(frozen=True)
class ContactCandidate:
    frame_index: int
    phase_id: str
    actor_region: str
    actor_vertex_id: int
    counterpart_id: str
    counterpart_frame: str
    contact_type: str
    world_point_m: Vec3
    world_counterpart: Pose
    actor_normal_world: Vec3
    counterpart_normal_world: Vec3
    surface_distance_m: float
    relative_speed_m_s: float
    visibility: float

    def __post_init__(self) -> None:
        if self.frame_index < 0 or self.actor_vertex_id < 0:
            raise ValueError("frame and vertex identifiers must be non-negative")
        if not all((self.phase_id, self.actor_region, self.counterpart_id, self.counterpart_frame)):
            raise ValueError("phase, actor region, and counterpart identifiers are required")
        if self.contact_type not in {"object", "environment", "self", "tool", "other"}:
            raise ValueError("unsupported contact_type")
        if self.surface_distance_m < 0 or self.relative_speed_m_s < 0:
            raise ValueError("distance and speed must be non-negative")
        if not 0 <= self.visibility <= 1:
            raise ValueError("visibility must be in [0, 1]")

    @property
    def counterpart_point_m(self) -> Vec3:
        return self.world_counterpart.inverse_transform_point(self.world_point_m)


@dataclass(frozen=True)
class ContactCompilerConfig:
    max_surface_distance_m: float = 0.012
    max_relative_speed_m_s: float = 0.08
    minimum_visibility: float = 0.35
    normal_opposition_cosine: float = 0.25
    cluster_epsilon_m: float = 0.014
    cluster_min_samples: int = 3
    minimum_temporal_support: int = 4
    max_frame_gap: int = 3

    def __post_init__(self) -> None:
        positive = (
            self.max_surface_distance_m,
            self.max_relative_speed_m_s,
            self.cluster_epsilon_m,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("metric thresholds must be positive")
        if not 0 <= self.minimum_visibility <= 1:
            raise ValueError("minimum_visibility must be in [0, 1]")
        if not 0 <= self.normal_opposition_cosine <= 1:
            raise ValueError("normal_opposition_cosine must be in [0, 1]")
        if self.cluster_min_samples < 2 or self.minimum_temporal_support < 2:
            raise ValueError("contact support thresholds must be at least two")


@dataclass(frozen=True)
class ContactCompilationResult:
    anchors: tuple[ContactAnchor, ...]
    candidates_seen: int
    candidates_kept: int
    rejection_counts: dict[str, int]
    groups_without_stable_contact: tuple[str, ...]


@dataclass(frozen=True)
class _CanonicalCandidate:
    source: ContactCandidate
    point_m: Vec3


class StableContactCompiler:
    """Paper-derived C2Dex contact extraction, owned and tested by FORGE.

    Candidates are filtered in world space, transformed into each object's canonical
    frame, split into locally stable temporal segments, clustered with DBSCAN, and
    represented by the dominant cluster medoid. No learned model may override these
    geometric checks.
    """

    def __init__(self, config: ContactCompilerConfig | None = None) -> None:
        self.config = config or ContactCompilerConfig()

    def compile(self, candidates: tuple[ContactCandidate, ...]) -> ContactCompilationResult:
        rejection_counts: defaultdict[str, int] = defaultdict(int)
        kept: list[_CanonicalCandidate] = []
        for candidate in candidates:
            reason = self._rejection_reason(candidate)
            if reason:
                rejection_counts[reason] += 1
                continue
            kept.append(_CanonicalCandidate(candidate, candidate.counterpart_point_m))

        groups: defaultdict[tuple[str, str, str, str, str], list[_CanonicalCandidate]] = defaultdict(list)
        for candidate in kept:
            source = candidate.source
            groups[
                (
                    source.phase_id,
                    source.actor_region,
                    source.counterpart_id,
                    source.counterpart_frame,
                    source.contact_type,
                )
            ].append(candidate)

        anchors: list[ContactAnchor] = []
        missing: list[str] = []
        for group_key in sorted(groups):
            stable_cluster = self._dominant_stable_cluster(groups[group_key])
            phase_id, actor_region, counterpart_id, counterpart_frame, contact_type = group_key
            if stable_cluster is None:
                missing.append(f"{phase_id}:{actor_region}:{counterpart_id}")
                continue
            anchors.append(
                self._to_anchor(
                    phase_id,
                    actor_region,
                    counterpart_id,
                    counterpart_frame,
                    contact_type,
                    stable_cluster,
                    len(anchors),
                )
            )

        return ContactCompilationResult(
            anchors=tuple(anchors),
            candidates_seen=len(candidates),
            candidates_kept=len(kept),
            rejection_counts=dict(sorted(rejection_counts.items())),
            groups_without_stable_contact=tuple(missing),
        )

    def _rejection_reason(self, candidate: ContactCandidate) -> str | None:
        if candidate.surface_distance_m > self.config.max_surface_distance_m:
            return "CONTACT_DISTANCE_EXCEEDED"
        if candidate.relative_speed_m_s > self.config.max_relative_speed_m_s:
            return "CONTACT_RELATIVE_MOTION_EXCEEDED"
        if candidate.visibility < self.config.minimum_visibility:
            return "CONTACT_UNOBSERVED"
        actor_normal = normalize(candidate.actor_normal_world)
        counterpart_normal = normalize(candidate.counterpart_normal_world)
        if dot(actor_normal, counterpart_normal) > -self.config.normal_opposition_cosine:
            return "CONTACT_NORMALS_NOT_OPPOSED"
        return None

    def _dominant_stable_cluster(
        self, candidates: list[_CanonicalCandidate]
    ) -> list[_CanonicalCandidate] | None:
        ordered = sorted(candidates, key=lambda item: item.source.frame_index)
        temporal_segments: list[list[_CanonicalCandidate]] = []
        current: list[_CanonicalCandidate] = []
        previous_frame: int | None = None
        for candidate in ordered:
            frame = candidate.source.frame_index
            if previous_frame is not None and frame - previous_frame > self.config.max_frame_gap:
                temporal_segments.append(current)
                current = []
            current.append(candidate)
            previous_frame = frame
        if current:
            temporal_segments.append(current)

        clusters: list[list[_CanonicalCandidate]] = []
        for segment in temporal_segments:
            for cluster in self._dbscan(segment):
                support = {item.source.frame_index for item in cluster}
                if len(support) >= self.config.minimum_temporal_support:
                    clusters.append(cluster)
        if not clusters:
            return None
        return max(
            clusters,
            key=lambda cluster: (
                len({item.source.frame_index for item in cluster}),
                len(cluster),
                -self._cluster_spread(cluster),
            ),
        )

    def _dbscan(self, points: list[_CanonicalCandidate]) -> list[list[_CanonicalCandidate]]:
        unvisited = set(range(len(points)))
        assigned: set[int] = set()
        clusters: list[list[_CanonicalCandidate]] = []

        while unvisited:
            seed = min(unvisited)
            unvisited.remove(seed)
            neighbours = self._region_query(points, seed)
            if len(neighbours) < self.config.cluster_min_samples:
                continue
            cluster_indices: set[int] = set()
            queue = deque(sorted(neighbours))
            while queue:
                index = queue.popleft()
                if index in unvisited:
                    unvisited.remove(index)
                    nearby = self._region_query(points, index)
                    if len(nearby) >= self.config.cluster_min_samples:
                        for neighbour in sorted(nearby):
                            if neighbour not in cluster_indices:
                                queue.append(neighbour)
                if index not in assigned:
                    assigned.add(index)
                    cluster_indices.add(index)
            clusters.append([points[index] for index in sorted(cluster_indices)])
        return clusters

    def _region_query(self, points: list[_CanonicalCandidate], index: int) -> set[int]:
        center = points[index].point_m
        return {
            candidate_index
            for candidate_index, candidate in enumerate(points)
            if distance(center, candidate.point_m) <= self.config.cluster_epsilon_m
        }

    @staticmethod
    def _cluster_spread(cluster: list[_CanonicalCandidate]) -> float:
        if not cluster:
            return float("inf")
        medoid = StableContactCompiler._medoid(cluster)
        return sum(distance(medoid.point_m, point.point_m) for point in cluster) / len(cluster)

    @staticmethod
    def _medoid(cluster: list[_CanonicalCandidate]) -> _CanonicalCandidate:
        return min(
            cluster,
            key=lambda candidate: sum(
                distance(candidate.point_m, other.point_m) for other in cluster
            ),
        )

    def _to_anchor(
        self,
        phase_id: str,
        actor_region: str,
        counterpart_id: str,
        counterpart_frame: str,
        contact_type: str,
        cluster: list[_CanonicalCandidate],
        anchor_index: int,
    ) -> ContactAnchor:
        medoid = self._medoid(cluster)
        support_frames = tuple(sorted({item.source.frame_index for item in cluster}))
        frame_span = max(support_frames) - min(support_frames) + 1
        temporal_coverage = len(support_frames) / frame_span
        support_score = min(1.0, len(support_frames) / self.config.minimum_temporal_support)
        observability = sum(item.source.visibility for item in cluster) / len(cluster)
        confidence = min(1.0, 0.4 * support_score + 0.3 * temporal_coverage + 0.3 * observability)
        variance = sum(distance(item.point_m, medoid.point_m) ** 2 for item in cluster) / len(cluster)
        return ContactAnchor(
            anchor_id=f"contact_{anchor_index:04d}",
            phase_id=phase_id,
            actor_region=actor_region,
            counterpart_id=counterpart_id,
            counterpart_frame=counterpart_frame,
            counterpart_point_m=medoid.point_m,
            contact_type=contact_type,
            support_frames=support_frames,
            confidence=confidence,
            uncertainty_m=sqrt(variance),
            observability=observability,
        )
