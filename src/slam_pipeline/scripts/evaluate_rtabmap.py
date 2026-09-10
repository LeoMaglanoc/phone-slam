"""Export and evaluate an RTAB-Map trajectory against TUM ground truth."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..dataset.tum_rgbd import _read_groundtruth
from ..evaluation.trajectory import evaluate_trajectories
from ..ros.trajectory_export import read_rtabmap_trajectory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    timestamps, poses = read_rtabmap_trajectory(args.database)
    trajectory_path = args.output / "rtabmap_trajectory.txt"
    from ..evaluation.trajectory import poses_to_tum

    poses_to_tum(timestamps, poses, trajectory_path)
    groundtruth = _read_groundtruth(args.dataset / "groundtruth.txt")
    gt_timestamps = __import__("numpy").asarray([item[0] for item in groundtruth], dtype=float)
    gt_poses = [item[1] for item in groundtruth]
    metrics = evaluate_trajectories(gt_timestamps, gt_poses, timestamps, poses, args.output)
    metrics["trajectory_path"] = str(trajectory_path)
    (args.output / "trajectory_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
