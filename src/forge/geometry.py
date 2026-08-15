from __future__ import annotations

from dataclasses import dataclass
from math import isclose, sqrt
from typing import Iterable

Vec3 = tuple[float, float, float]
Mat3 = tuple[Vec3, Vec3, Vec3]


def vec3(value: Iterable[float]) -> Vec3:
    result = tuple(float(v) for v in value)
    if len(result) != 3:
        raise ValueError("expected three components")
    return result  # type: ignore[return-value]


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a: Vec3, factor: float) -> Vec3:
    return (a[0] * factor, a[1] * factor, a[2] * factor)


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a: Vec3) -> float:
    return sqrt(dot(a, a))


def distance(a: Vec3, b: Vec3) -> float:
    return norm(sub(a, b))


def normalize(a: Vec3) -> Vec3:
    length = norm(a)
    if length <= 1e-12:
        raise ValueError("cannot normalize a zero vector")
    return scale(a, 1.0 / length)


def transpose(matrix: Mat3) -> Mat3:
    return (
        (matrix[0][0], matrix[1][0], matrix[2][0]),
        (matrix[0][1], matrix[1][1], matrix[2][1]),
        (matrix[0][2], matrix[1][2], matrix[2][2]),
    )


def matvec(matrix: Mat3, vector: Vec3) -> Vec3:
    return (
        dot(matrix[0], vector),
        dot(matrix[1], vector),
        dot(matrix[2], vector),
    )


def matmul(left: Mat3, right: Mat3) -> Mat3:
    columns = transpose(right)
    return tuple(tuple(dot(row, col) for col in columns) for row in left)  # type: ignore[return-value]


def determinant(matrix: Mat3) -> float:
    a, b, c = matrix
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


IDENTITY_ROTATION: Mat3 = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def validate_rotation(matrix: Mat3, tolerance: float = 1e-5) -> None:
    product = matmul(matrix, transpose(matrix))
    for row in range(3):
        for column in range(3):
            expected = 1.0 if row == column else 0.0
            if not isclose(product[row][column], expected, abs_tol=tolerance):
                raise ValueError("rotation matrix must be orthonormal")
    if not isclose(determinant(matrix), 1.0, abs_tol=tolerance):
        raise ValueError("rotation matrix must have determinant +1")


@dataclass(frozen=True)
class Pose:
    """Rigid transform with meters and a right-handed rotation matrix."""

    rotation: Mat3 = IDENTITY_ROTATION
    translation_m: Vec3 = (0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        validate_rotation(self.rotation)
        if len(self.translation_m) != 3:
            raise ValueError("translation must contain three meter values")

    @classmethod
    def identity(cls) -> "Pose":
        return cls()

    def transform_point(self, point: Vec3) -> Vec3:
        return add(matvec(self.rotation, point), self.translation_m)

    def inverse_transform_point(self, point: Vec3) -> Vec3:
        return matvec(transpose(self.rotation), sub(point, self.translation_m))

    def inverse(self) -> "Pose":
        inverse_rotation = transpose(self.rotation)
        inverse_translation = scale(matvec(inverse_rotation, self.translation_m), -1.0)
        return Pose(inverse_rotation, inverse_translation)

    def compose(self, child: "Pose") -> "Pose":
        return Pose(
            matmul(self.rotation, child.rotation),
            self.transform_point(child.translation_m),
        )

    def relative_to(self, parent: "Pose") -> "Pose":
        return parent.inverse().compose(self)

    def almost_equal(self, other: "Pose", tolerance: float = 1e-9) -> bool:
        return all(
            isclose(self.rotation[row][column], other.rotation[row][column], abs_tol=tolerance)
            for row in range(3)
            for column in range(3)
        ) and all(
            isclose(left, right, abs_tol=tolerance)
            for left, right in zip(self.translation_m, other.translation_m)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "rotation": [list(row) for row in self.rotation],
            "translation_m": list(self.translation_m),
        }
