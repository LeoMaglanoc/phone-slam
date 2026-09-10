"""Loader and timestamp association for the TUM RGB-D benchmark."""

from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.spatial.transform import Rotation

from .schema import CameraIntrinsics, Dataset, Frame


def _read_index(path: Path) -> list[tuple[float, str]]:
    records: list[tuple[float, str]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            records.append((float(parts[0]), parts[1]))
    return records


def _read_groundtruth(path: Path) -> list[tuple[float, np.ndarray]]:
    records: list[tuple[float, np.ndarray]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) != 8:
                continue
            timestamp, tx, ty, tz, qx, qy, qz, qw = map(float, parts)
            transform = np.eye(4, dtype=np.float64)
            transform[:3, :3] = Rotation.from_quat([qx, qy, qz, qw]).as_matrix()
            transform[:3, 3] = [tx, ty, tz]
            records.append((timestamp, transform))
    return records


def _associate(
    first: Iterable[tuple[float, object]],
    second: Iterable[tuple[float, object]],
    max_difference_s: float,
) -> list[tuple[tuple[float, object], tuple[float, object]]]:
    """Associate each first stream record with one nearest unused second record."""
    left = list(first)
    right = list(second)
    associations = []
    j = 0
    for current in left:
        timestamp = current[0]
        while j + 1 < len(right) and abs(right[j + 1][0] - timestamp) <= abs(right[j][0] - timestamp):
            j += 1
        if right and abs(right[j][0] - timestamp) <= max_difference_s:
            associations.append((current, right[j]))
    return associations


def load_tum_dataset(
    root: str | Path,
    *,
    intrinsics: CameraIntrinsics | None = None,
    max_rgb_depth_difference_s: float = 0.02,
    max_pose_difference_s: float = 0.02,
) -> Dataset:
    root = Path(root)
    if intrinsics is None:
        intrinsics = CameraIntrinsics(640, 480, 525.0, 525.0, 319.5, 239.5)
    required = [root / "rgb.txt", root / "depth.txt", root / "groundtruth.txt"]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing TUM files: " + ", ".join(missing))

    rgb = _read_index(root / "rgb.txt")
    depth = _read_index(root / "depth.txt")
    groundtruth = _read_groundtruth(root / "groundtruth.txt")
    rgb_depth = _associate(rgb, depth, max_rgb_depth_difference_s)
    frames: list[Frame] = []
    for frame_id, (rgb_record, depth_record) in enumerate(rgb_depth):
        rgb_timestamp, rgb_relative = rgb_record
        depth_timestamp, depth_relative = depth_record
        pose_matches = _associate(
            [(rgb_timestamp, None)], groundtruth, max_pose_difference_s
        )
        if not pose_matches:
            continue
        pose_timestamp, pose = pose_matches[0][1]
        frames.append(
            Frame(
                frame_id=frame_id,
                timestamp_ns=round(rgb_timestamp * 1e9),
                rgb_path=root / rgb_relative,
                depth_path=root / depth_relative,
                depth_timestamp_ns=round(depth_timestamp * 1e9),
                pose_timestamp_ns=round(pose_timestamp * 1e9),
                T_world_camera=pose,
                intrinsics=intrinsics,
            )
        )
    if not frames:
        raise RuntimeError(f"No associated RGB/depth/ground-truth frames found in {root}")
    return Dataset(root=root, intrinsics=intrinsics, frames=frames, name=root.name)

