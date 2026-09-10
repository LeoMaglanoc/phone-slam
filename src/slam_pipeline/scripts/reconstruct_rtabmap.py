"""Fuse RGB-D frames at the optimized poses stored in an RTAB-Map database."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import yaml

from ..dataset.schema import CameraIntrinsics, Dataset
from ..dataset.tum_rgbd import load_tum_dataset
from ..reconstruction.tsdf import reconstruct_tsdf
from ..ros.trajectory_export import read_rtabmap_trajectory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-difference-s", type=float, default=0.05)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    camera = config["camera"]
    intrinsics = CameraIntrinsics(
        width=int(camera["width"]), height=int(camera["height"]), fx=float(camera["fx"]), fy=float(camera["fy"]),
        cx=float(camera["cx"]), cy=float(camera["cy"]), depth_scale=float(camera.get("depth_scale", 5000.0)),
        depth_trunc=float(camera.get("depth_trunc", 4.0)),
    )
    association = config.get("association", {})
    dataset = load_tum_dataset(
        args.dataset,
        intrinsics=intrinsics,
        max_rgb_depth_difference_s=float(association.get("max_rgb_depth_difference_s", 0.02)),
        max_pose_difference_s=float(association.get("max_pose_difference_s", 0.02)),
    )
    estimate_timestamps, estimate_poses = read_rtabmap_trajectory(args.database)
    dataset_timestamps = np.asarray([frame.timestamp_ns / 1e9 for frame in dataset.frames])
    selected = []
    used: set[int] = set()
    for timestamp, pose in zip(estimate_timestamps, estimate_poses):
        frame_id = int(np.argmin(np.abs(dataset_timestamps - timestamp)))
        if frame_id in used or abs(dataset_timestamps[frame_id] - timestamp) > args.max_difference_s:
            continue
        used.add(frame_id)
        selected.append(replace(dataset.frames[frame_id], T_world_camera=pose))
    if not selected:
        raise RuntimeError("No RTAB-Map nodes could be associated with dataset frames")
    optimized = Dataset(root=dataset.root, intrinsics=dataset.intrinsics, frames=selected, name="rtabmap_optimized")
    tsdf = config["tsdf"]
    result = reconstruct_tsdf(
        optimized,
        args.output,
        voxel_length=float(tsdf["voxel_length"]),
        sdf_trunc=float(tsdf["sdf_trunc"]),
        frame_stride=1,
        output_prefix="optimized",
    )
    result["associated_frames"] = len(selected)
    result["database"] = str(args.database)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "rtabmap_tsdf_stats.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
