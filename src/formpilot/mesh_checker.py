from pathlib import Path

import trimesh
from pydantic import BaseModel, Field


class MeshReport(BaseModel):
    passed: bool
    watertight: bool
    component_count: int
    extents: tuple[float, float, float]
    issue_codes: list[str] = Field(default_factory=list)


def _component_count(mesh: trimesh.Trimesh) -> int:
    """Count components joined by shared face edges without graph engines."""
    if len(mesh.faces) == 0:
        return 0

    parents = list(range(len(mesh.faces)))
    sizes = [1] * len(mesh.faces)

    def find(face_index: int) -> int:
        root = face_index
        while parents[root] != root:
            root = parents[root]
        while face_index != root:
            parent = parents[face_index]
            parents[face_index] = root
            face_index = parent
        return root

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        if sizes[left_root] < sizes[right_root]:
            left_root, right_root = right_root, left_root
        parents[right_root] = left_root
        sizes[left_root] += sizes[right_root]

    edge_owner: dict[tuple[int, int], int] = {}
    for face_index, face in enumerate(mesh.faces):
        first, second, third = (int(vertex) for vertex in face)
        for edge in ((first, second), (second, third), (third, first)):
            normalized_edge = tuple(sorted(edge))
            previous_face = edge_owner.setdefault(normalized_edge, face_index)
            if previous_face != face_index:
                union(face_index, previous_face)
    return len({find(face_index) for face_index in range(len(mesh.faces))})


def check_mesh(
    path: Path,
    expected_width: float,
    expected_depth: float | None = None,
    expected_height: float | None = None,
) -> MeshReport:
    loaded = trimesh.load_mesh(path, force="mesh")
    issue_codes: list[str] = []
    if len(loaded.vertices) == 0 or len(loaded.faces) == 0:
        issue_codes.append("empty_mesh")
    component_count = _component_count(loaded)
    if component_count != 1:
        issue_codes.append("unexpected_components")
    if not loaded.is_watertight:
        issue_codes.append("not_watertight")
    raw_extents = loaded.extents
    extents = (
        tuple(float(value) for value in raw_extents)
        if raw_extents is not None
        else (0.0, 0.0, 0.0)
    )
    if abs(extents[0] - expected_width) > 0.5:
        issue_codes.append("width_mismatch")
    if expected_depth is not None and abs(extents[1] - expected_depth) > 0.5:
        issue_codes.append("depth_mismatch")
    if expected_height is not None and abs(extents[2] - expected_height) > 0.5:
        issue_codes.append("height_mismatch")
    return MeshReport(
        passed=not issue_codes,
        watertight=bool(loaded.is_watertight),
        component_count=component_count,
        extents=extents,
        issue_codes=issue_codes,
    )
