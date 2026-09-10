"""Fail on missing, empty, or non-finite completed benchmark artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _require_file(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Required artifact missing or empty: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output
    for path in [
        output / "rtabmap.db",
        output / "evaluation" / "optimized_trajectory.txt",
        output / "evaluation" / "evo_crosscheck.json",
        output / "optimized_tsdf" / "optimized_tsdf_mesh.ply",
        output / "optimized_tsdf" / "optimized_pointcloud.ply",
        output / "report.md",
    ]:
        _require_file(path)
    stats = json.loads((output / "optimized_tsdf" / "rtabmap_tsdf_stats.json").read_text(encoding="utf-8"))
    for key in ("mesh_vertices", "mesh_triangles", "point_count"):
        if int(stats.get(key, 0)) <= 0:
            raise RuntimeError(f"Invalid reconstruction statistic {key}: {stats.get(key)}")
    metrics = json.loads((output / "evaluation" / "trajectory_metrics.json").read_text(encoding="utf-8"))
    if int(metrics.get("optimized", {}).get("associated_poses", 0)) <= 0:
        raise RuntimeError("Optimized trajectory has no associated poses")
    evo = json.loads((output / "evaluation" / "evo_crosscheck.json").read_text(encoding="utf-8"))
    if not evo.get("within_1e-5_tolerance", False):
        raise RuntimeError(f"Project trajectory metrics disagree with evo: {evo}")
    print(f"Validated benchmark artifacts: {output}")


if __name__ == "__main__":
    main()
