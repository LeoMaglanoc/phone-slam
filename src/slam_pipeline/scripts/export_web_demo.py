"""Export a metric RTAB-Map/Open3D run as static Three.js demo assets.

The conversion is deliberately performed here, once, rather than in browser
code. Both the GLB and trajectory use Three.js's Y-up coordinate convention.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import open3d as o3d
import yaml
from scipy.spatial.transform import Rotation

from ..evaluation.trajectory import read_tum_trajectory
from .sync_web_video_metadata import video_details


_TUM_DATASET_URL = "https://cvg.cit.tum.de/data/datasets/rgbd-dataset"
_CV_TO_THREE = np.diag([1.0, -1.0, -1.0, 1.0])


def convert_pose_to_threejs(T_world_camera: np.ndarray) -> np.ndarray:
    """Convert a right-handed OpenCV/robotics pose to the shared web basis."""
    pose = np.asarray(T_world_camera, dtype=np.float64)
    if pose.shape != (4, 4) or not np.isfinite(pose).all():
        raise ValueError("Expected a finite 4x4 camera pose")
    return _CV_TO_THREE @ pose @ _CV_TO_THREE


def _finite(value: Any) -> bool:
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, list):
        return all(_finite(item) for item in value)
    return not isinstance(value, float) or math.isfinite(value)


def _asset_path(public_dir: Path, value: str) -> Path:
    path = public_dir / value
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Required browser artifact missing or empty: {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public-dir", type=Path, required=True)
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    output, public = args.output, args.public_dir
    public.mkdir(parents=True, exist_ok=True)
    tsdf_dir = output / "optimized_tsdf"
    source_mesh = tsdf_dir / "optimized_tsdf_mesh.ply"
    source_preview = tsdf_dir / "optimized_mesh_preview.png"
    trajectory_source = output / "evaluation" / "optimized_trajectory.txt"
    for required in (source_mesh, source_preview, trajectory_source):
        if not required.is_file() or required.stat().st_size == 0:
            raise FileNotFoundError(required)

    mesh = o3d.io.read_triangle_mesh(str(source_mesh), enable_post_processing=True)
    if not mesh.has_vertices() or not mesh.has_triangles():
        raise RuntimeError(f"Could not read a non-empty mesh from {source_mesh}")
    mesh.compute_vertex_normals()
    original_vertices, original_triangles = len(mesh.vertices), len(mesh.triangles)
    web_export = config.get("web_export", {})
    target = int(web_export.get("target_triangles", original_triangles))
    if bool(web_export.get("simplify", False)) and original_triangles > target > 0:
        mesh = mesh.simplify_quadric_decimation(target)
        mesh.compute_vertex_normals()
    mesh.transform(_CV_TO_THREE)
    scene_path = public / "scene.glb"
    if not o3d.io.write_triangle_mesh(str(scene_path), mesh, write_vertex_normals=True, write_vertex_colors=True):
        raise RuntimeError(f"Open3D could not write {scene_path}; this build needs glTF/Assimp support")

    timestamps, poses = read_tum_trajectory(trajectory_source)
    first_timestamp = float(timestamps[0])
    samples = []
    for timestamp, pose in zip(timestamps, poses):
        converted = convert_pose_to_threejs(pose)
        quaternion = Rotation.from_matrix(converted[:3, :3]).as_quat()
        samples.append({
            "timestamp": float(timestamp - first_timestamp),
            "position": [float(value) for value in converted[:3, 3]],
            "quaternion": [float(value) for value in quaternion],
        })
    trajectory = {
        "units": "meters",
        "coordinate_convention": "threejs_world",
        "source": "rtabmap_global_pose_graph_optimized",
        "samples": samples,
    }
    if not samples or not _finite(trajectory):
        raise RuntimeError("Trajectory export is empty or non-finite")
    (public / "trajectory.json").write_text(json.dumps(trajectory, indent=2) + "\n", encoding="utf-8")

    image = cv2.imread(str(source_preview), cv2.IMREAD_COLOR)
    if image is None or not cv2.imwrite(str(public / "thumbnail.webp"), image, [cv2.IMWRITE_WEBP_QUALITY, 82]):
        raise RuntimeError("Could not write thumbnail.webp")
    metrics = json.loads((output / "evaluation" / "trajectory_metrics.json").read_text(encoding="utf-8"))
    graph = json.loads((output / "graph_stats.json").read_text(encoding="utf-8"))
    replay = json.loads((output / "replay_summary.json").read_text(encoding="utf-8"))
    video_info_path = output / "rgb_video_info.json"
    depth_video_info_path = output / "depth_video_info.json"
    if not video_info_path.is_file() or not depth_video_info_path.is_file():
        raise RuntimeError("Prepare RGB and depth videos with scripts/prepare_demo_video.sh before exporting the web demo")
    video_info = json.loads(video_info_path.read_text(encoding="utf-8"))
    depth_video_info = json.loads(depth_video_info_path.read_text(encoding="utf-8"))
    metadata = {
        "title": "TUM RGB-D — freiburg3_long_office_household",
        "dataset": {"name": "freiburg3_long_office_household", "family": "TUM RGB-D", "url": _TUM_DATASET_URL},
        "slam": {
            "input_frames": int(replay.get("published_rgb_frames", 0)),
            "odometry_poses": sum(1 for _ in (output / "odometry_poses.txt").open(encoding="utf-8")),
            "graph_nodes": int(graph.get("node_count", 0)), "graph_links": int(graph.get("link_count", 0)),
            "global_loop_closures": int(graph.get("global_loop_closure_count", 0)),
            "local_space_closures": int(graph.get("local_space_closure_count", 0)),
            "local_time_closures": int(graph.get("local_time_closure_count", 0)),
        },
        "accuracy": {
            "ate_rmse_m": float(metrics["optimized"]["ate_rmse_m"]),
            "rpe_translation_rmse_m": float(metrics["optimized"]["rpe_translation_rmse_m"]),
            "rpe_rotation_rmse_rad": float(metrics["optimized"]["rpe_rotation_rmse_rad"]),
        },
        "mesh": {"vertices": len(mesh.vertices), "triangles": len(mesh.triangles), "original_vertices": original_vertices, "original_triangles": original_triangles},
        "video": video_details(video_info),
        "depth_video": {**video_details(depth_video_info), "visualization": "Turbo colorized metric depth; black pixels are invalid measurements."},
        "assets": {"video": "demo.mp4", "depth_video": "depth.mp4", "mesh": "scene.glb", "trajectory": "trajectory.json", "thumbnail": "thumbnail.webp"},
    }
    metadata["mesh"]["glb_size_bytes"] = scene_path.stat().st_size
    if not _finite(metadata):
        raise RuntimeError("Metadata contains a non-finite number")
    (public / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (public / "attribution.txt").write_text(
        "Canonical example: TUM RGB-D Dataset — freiburg3_long_office_household\n"
        f"Source: {_TUM_DATASET_URL}\n"
        "The official TUM RGB AVI and colorized TUM depth frames are transcoded for browser playback.\n",
        encoding="utf-8",
    )
    # Video probe data has been embedded in metadata; keep the public bundle
    # limited to the documented browser-facing files.
    video_info_path.unlink()
    depth_video_info_path.unlink()
    for asset in ("demo.mp4", "depth.mp4", "scene.glb", "trajectory.json", "metadata.json", "thumbnail.webp", "attribution.txt"):
        _asset_path(public, asset)
    print(json.dumps({"public_dir": str(public), "trajectory_samples": len(samples), "glb_size_bytes": scene_path.stat().st_size}, indent=2))


if __name__ == "__main__":
    main()
