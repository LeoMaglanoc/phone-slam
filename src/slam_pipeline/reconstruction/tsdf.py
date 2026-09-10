"""Open3D TSDF reconstruction using the normalized dataset abstraction."""

from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import open3d as o3d

from ..dataset.schema import Dataset, Frame


def _read_rgbd(frame: Frame) -> o3d.geometry.RGBDImage:
    color = cv2.imread(str(frame.rgb_path), cv2.IMREAD_COLOR)
    depth = cv2.imread(str(frame.depth_path), cv2.IMREAD_UNCHANGED)
    if color is None:
        raise IOError(f"Could not read RGB image: {frame.rgb_path}")
    if depth is None and frame.depth_path.suffix == ".bin":
        if frame.intrinsics.depth_width is None or frame.intrinsics.depth_height is None:
            raise ValueError("Binary phone depth requires depth dimensions in CameraIntrinsics")
        expected = frame.intrinsics.depth_width * frame.intrinsics.depth_height
        values = np.fromfile(frame.depth_path, dtype="<u2")
        if values.size != expected:
            raise ValueError(f"Unexpected binary depth size in {frame.depth_path}: {values.size} != {expected}")
        depth = values.reshape(frame.intrinsics.depth_height, frame.intrinsics.depth_width)
    if depth is None:
        raise IOError(f"Could not read depth image: {frame.depth_path}")
    if depth.shape[:2] != color.shape[:2]:
        depth = cv2.resize(depth, (color.shape[1], color.shape[0]), interpolation=cv2.INTER_NEAREST)
    if frame.confidence_path is not None and frame.intrinsics.confidence_min > 0:
        confidence = cv2.imread(str(frame.confidence_path), cv2.IMREAD_UNCHANGED)
        if confidence is None and frame.confidence_path.suffix == ".bin":
            if frame.intrinsics.depth_width is None or frame.intrinsics.depth_height is None:
                raise ValueError("Binary confidence requires depth dimensions in CameraIntrinsics")
            confidence = np.fromfile(frame.confidence_path, dtype=np.uint8).reshape(
                frame.intrinsics.depth_height, frame.intrinsics.depth_width
            )
        if confidence is not None:
            confidence = cv2.resize(confidence, (color.shape[1], color.shape[0]), interpolation=cv2.INTER_NEAREST)
            depth[confidence < frame.intrinsics.confidence_min] = 0
    color = cv2.cvtColor(color, cv2.COLOR_BGR2RGB)
    color_image = o3d.geometry.Image(np.ascontiguousarray(color))
    depth_image = o3d.geometry.Image(np.ascontiguousarray(depth))
    return o3d.geometry.RGBDImage.create_from_color_and_depth(
        color_image,
        depth_image,
        depth_scale=frame.intrinsics.depth_scale,
        depth_trunc=frame.intrinsics.depth_trunc,
        convert_rgb_to_intensity=False,
    )


def reconstruct_tsdf(
    dataset: Dataset,
    output_dir: str | Path,
    *,
    voxel_length: float = 0.03,
    sdf_trunc: float = 0.06,
    frame_stride: int = 1,
    output_prefix: str = "gt",
) -> dict[str, object]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if frame_stride < 1:
        raise ValueError("frame_stride must be >= 1")
    intrinsics = o3d.camera.PinholeCameraIntrinsic(
        dataset.intrinsics.width,
        dataset.intrinsics.height,
        dataset.intrinsics.fx,
        dataset.intrinsics.fy,
        dataset.intrinsics.cx,
        dataset.intrinsics.cy,
    )
    volume = o3d.pipelines.integration.ScalableTSDFVolume(
        voxel_length=voxel_length,
        sdf_trunc=sdf_trunc,
        color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8,
    )
    integrated = 0
    for index, frame in enumerate(dataset.frames):
        if index % frame_stride:
            continue
        rgbd = _read_rgbd(frame)
        # Open3D's integrate() wants world-to-camera, while our public
        # convention is camera-to-world.
        volume.integrate(rgbd, intrinsics, np.linalg.inv(frame.T_world_camera))
        integrated += 1
    if integrated == 0:
        raise RuntimeError("No frames were integrated")

    mesh = volume.extract_triangle_mesh()
    pointcloud = volume.extract_point_cloud()
    mesh.compute_vertex_normals()
    mesh_path = output_dir / f"{output_prefix}_tsdf_mesh.ply"
    cloud_path = output_dir / f"{output_prefix}_pointcloud.ply"
    if not o3d.io.write_triangle_mesh(str(mesh_path), mesh):
        raise IOError(f"Failed to write {mesh_path}")
    if not o3d.io.write_point_cloud(str(cloud_path), pointcloud):
        raise IOError(f"Failed to write {cloud_path}")
    preview_path = output_dir / f"{output_prefix}_mesh_preview.png"
    _write_geometry_preview(pointcloud, preview_path, f"{output_prefix} TSDF point cloud")
    trajectory_path = output_dir / f"{output_prefix}_trajectory.png"
    _write_trajectory_preview(dataset, trajectory_path, f"{output_prefix} camera trajectory")
    result = validate_geometry(mesh, pointcloud)
    result.update(
        {
            "integrated_frames": integrated,
            "mesh_path": str(mesh_path),
            "pointcloud_path": str(cloud_path),
            "mesh_preview_path": str(preview_path),
            "trajectory_path": str(trajectory_path),
        }
    )
    return result


def validate_geometry(mesh: o3d.geometry.TriangleMesh, pointcloud: o3d.geometry.PointCloud) -> dict[str, object]:
    vertices = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)
    points = np.asarray(pointcloud.points)
    if len(vertices) == 0 or len(triangles) == 0 or len(points) == 0:
        raise RuntimeError("Reconstruction geometry is empty")
    if not np.isfinite(vertices).all() or not np.isfinite(points).all():
        raise RuntimeError("Reconstruction geometry contains NaN/Inf")
    bounds = np.stack([points.min(axis=0), points.max(axis=0)])
    if not np.isfinite(bounds).all():
        raise RuntimeError("Reconstruction bounding box is not finite")
    return {
        "mesh_vertices": int(len(vertices)),
        "mesh_triangles": int(len(triangles)),
        "point_count": int(len(points)),
        "bounding_box_min": bounds[0].tolist(),
        "bounding_box_max": bounds[1].tolist(),
        "bounding_box_size": (bounds[1] - bounds[0]).tolist(),
    }


def _write_geometry_preview(pointcloud: o3d.geometry.PointCloud, path: Path, title: str) -> None:
    points = np.asarray(pointcloud.points)
    sample = points[:: max(1, len(points) // 10000)]
    fig = plt.figure(figsize=(9, 7))
    axis = fig.add_subplot(111, projection="3d")
    axis.scatter(sample[:, 0], sample[:, 1], sample[:, 2], s=0.4, c=sample[:, 2], cmap="viridis")
    axis.set_title(title)
    axis.set_xlabel("x (m)")
    axis.set_ylabel("y (m)")
    axis.set_zlabel("z (m)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _write_trajectory_preview(dataset: Dataset, path: Path, title: str) -> None:
    positions = np.array([frame.T_world_camera[:3, 3] for frame in dataset.frames])
    fig = plt.figure(figsize=(9, 7))
    axis = fig.add_subplot(111, projection="3d")
    axis.plot(positions[:, 0], positions[:, 1], positions[:, 2], linewidth=1.5)
    axis.scatter(*positions[0], c="green", label="start")
    axis.scatter(*positions[-1], c="red", label="end")
    axis.set_title(title)
    axis.set_xlabel("x (m)")
    axis.set_ylabel("y (m)")
    axis.set_zlabel("z (m)")
    axis.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
