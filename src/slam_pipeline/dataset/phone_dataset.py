"""Loader for the Android recorder's ``offline-slam-phone-v1`` directory."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from .schema import CameraIntrinsics, Dataset, Frame


def load_phone_dataset(root: str | Path) -> Dataset:
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != "offline-slam-phone-v1":
        raise ValueError(f"Unsupported phone dataset format: {manifest.get('format')!r}")
    poses = {}
    with (root / "poses.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            poses[int(row["timestamp_ns"])] = row
    intrinsics = CameraIntrinsics(
        width=int(manifest["rgb_width"]), height=int(manifest["rgb_height"]), fx=float(manifest["fx"]),
        fy=float(manifest["fy"]), cx=float(manifest["cx"]), cy=float(manifest["cy"]),
        depth_scale=1.0 / float(manifest.get("depth_scale", 0.001)),
        depth_trunc=float(manifest.get("depth_trunc", 15.0)),
        depth_width=int(manifest["depth_width"]), depth_height=int(manifest["depth_height"]),
        confidence_min=int(manifest.get("confidence_min", 0)),
    )
    frames = []
    with (root / "frames.csv").open(newline="", encoding="utf-8") as stream:
        for frame_id, row in enumerate(csv.DictReader(stream)):
            timestamp_ns = int(row["timestamp_ns"])
            pose_row = poses.get(timestamp_ns)
            if pose_row is None:
                continue
            transform = np.eye(4, dtype=np.float64)
            transform[:3, :3] = Rotation.from_quat([
                float(pose_row["qx"]), float(pose_row["qy"]), float(pose_row["qz"]), float(pose_row["qw"]),
            ]).as_matrix()
            transform[:3, 3] = [float(pose_row["tx"]), float(pose_row["ty"]), float(pose_row["tz"])]
            frames.append(Frame(
                frame_id=frame_id, timestamp_ns=timestamp_ns, rgb_path=root / row["rgb_path"],
                depth_path=root / row["depth_path"], confidence_path=root / row["confidence_path"],
                depth_timestamp_ns=int(row["depth_timestamp_ns"]), pose_timestamp_ns=timestamp_ns,
                T_world_camera=transform, intrinsics=intrinsics,
            ))
    if not frames:
        raise RuntimeError(f"No complete frames found in {root}")
    return Dataset(root=root, intrinsics=intrinsics, frames=frames, name=root.name)
