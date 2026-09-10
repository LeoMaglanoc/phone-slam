"""Replay a dataset as ROS 2 RGB-D and external-odometry topics."""

from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Quaternion, TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile
from sensor_msgs.msg import CameraInfo, Image
from scipy.spatial.transform import Rotation
from tf2_ros import TransformBroadcaster

from ..dataset.schema import Dataset, Frame
from ..dataset.phone_dataset import load_phone_dataset
from ..dataset.tum_rgbd import load_tum_dataset


def _stamp(timestamp_ns: int, message: Image | CameraInfo | Odometry) -> None:
    message.header.stamp.sec = int(timestamp_ns // 1_000_000_000)
    message.header.stamp.nanosec = int(timestamp_ns % 1_000_000_000)


def _quaternion(rotation: np.ndarray) -> Quaternion:
    x, y, z, w = Rotation.from_matrix(rotation).as_quat()
    return Quaternion(x=float(x), y=float(y), z=float(z), w=float(w))


class DatasetPlayer(Node):
    """Publish one recorded RGB-D frame and its matching odometry pose."""

    def __init__(
        self,
        dataset: Dataset,
        *,
        rate: float,
        max_frames: int | None,
        rgb_topic: str,
        depth_topic: str,
        camera_info_topic: str,
        odom_topic: str,
    ) -> None:
        super().__init__("dataset_player")
        qos = QoSProfile(depth=10)
        self._dataset = dataset
        self._rate = rate
        self._max_frames = max_frames
        self._bridge = CvBridge()
        self._rgb_pub = self.create_publisher(Image, rgb_topic, qos)
        self._depth_pub = self.create_publisher(Image, depth_topic, qos)
        self._camera_info_pub = self.create_publisher(CameraInfo, camera_info_topic, qos)
        self._odom_pub = self.create_publisher(Odometry, odom_topic, qos)
        self._tf_broadcaster = TransformBroadcaster(self)
        self._thread = threading.Thread(target=self._publish_all, daemon=True)
        self._thread.start()

    def _camera_info(self, frame: Frame) -> CameraInfo:
        camera = frame.intrinsics
        message = CameraInfo()
        message.header.frame_id = "camera_link"
        message.width = camera.width
        message.height = camera.height
        message.distortion_model = "plumb_bob"
        message.k = [camera.fx, 0.0, camera.cx, 0.0, camera.fy, camera.cy, 0.0, 0.0, 1.0]
        message.d = [0.0] * 5
        message.r = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        message.p = [camera.fx, 0.0, camera.cx, 0.0, 0.0, camera.fy, camera.cy, 0.0, 0.0, 0.0, 1.0, 0.0]
        return message

    def _publish_frame(self, frame: Frame) -> None:
        color = cv2.imread(str(frame.rgb_path), cv2.IMREAD_COLOR)
        depth = cv2.imread(str(frame.depth_path), cv2.IMREAD_UNCHANGED)
        if color is None or depth is None:
            raise FileNotFoundError(f"Could not read frame {frame.frame_id}: {frame.rgb_path} / {frame.depth_path}")
        if color.shape[:2] != (frame.intrinsics.height, frame.intrinsics.width):
            raise ValueError(f"Unexpected RGB shape {color.shape} for frame {frame.frame_id}")
        if depth.shape[:2] != color.shape[:2]:
            raise ValueError(f"RGB/depth shape mismatch for frame {frame.frame_id}")

        stamp_ns = frame.timestamp_ns
        rgb_message = self._bridge.cv2_to_imgmsg(cv2.cvtColor(color, cv2.COLOR_BGR2RGB), encoding="rgb8")
        depth_message = self._bridge.cv2_to_imgmsg(depth, encoding="16UC1")
        rgb_message.header.frame_id = "camera_link"
        depth_message.header.frame_id = "camera_link"
        _stamp(stamp_ns, rgb_message)
        _stamp(stamp_ns, depth_message)
        info_message = self._camera_info(frame)
        _stamp(stamp_ns, info_message)

        odom = Odometry()
        odom.header.frame_id = "odom"
        odom.child_frame_id = "camera_link"
        _stamp(stamp_ns, odom)
        odom.pose.pose.position.x = float(frame.T_world_camera[0, 3])
        odom.pose.pose.position.y = float(frame.T_world_camera[1, 3])
        odom.pose.pose.position.z = float(frame.T_world_camera[2, 3])
        odom.pose.pose.orientation = _quaternion(frame.T_world_camera[:3, :3])
        odom.pose.covariance[0] = odom.pose.covariance[7] = odom.pose.covariance[14] = 1e-6
        odom.pose.covariance[21] = odom.pose.covariance[28] = odom.pose.covariance[35] = 1e-6

        transform = TransformStamped()
        transform.header = odom.header
        transform.child_frame_id = "camera_link"
        transform.transform.translation.x = odom.pose.pose.position.x
        transform.transform.translation.y = odom.pose.pose.position.y
        transform.transform.translation.z = odom.pose.pose.position.z
        transform.transform.rotation = odom.pose.pose.orientation

        # Odometry is sent first so RTAB-Map can associate it with the sensor frame.
        self._odom_pub.publish(odom)
        self._tf_broadcaster.sendTransform(transform)
        self._rgb_pub.publish(rgb_message)
        self._depth_pub.publish(depth_message)
        self._camera_info_pub.publish(info_message)

    def _publish_all(self) -> None:
        frames = self._dataset.frames[: self._max_frames]
        previous_timestamp_ns: int | None = None
        try:
            for frame in frames:
                if previous_timestamp_ns is not None:
                    delay_s = max(0.0, (frame.timestamp_ns - previous_timestamp_ns) / 1e9 / self._rate)
                    time.sleep(delay_s)
                self._publish_frame(frame)
                previous_timestamp_ns = frame.timestamp_ns
            self.get_logger().info(f"Published {len(frames)} frames from {self._dataset.name}")
        except Exception as error:  # pragma: no cover - exercised by live replay
            self.get_logger().error(str(error))
        finally:
            self._done = True


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--rate", type=float, default=4.0, help="Playback multiplier; default is 4x real time.")
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--rgb-topic", default="/camera/rgb/image_rect_color")
    parser.add_argument("--depth-topic", default="/camera/depth_registered/image_raw")
    parser.add_argument("--camera-info-topic", default="/camera/rgb/camera_info")
    parser.add_argument("--odom-topic", default="/odom")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    config = __import__("yaml").safe_load(args.config.read_text(encoding="utf-8"))
    camera = config["camera"]
    from ..dataset.schema import CameraIntrinsics

    intrinsics = CameraIntrinsics(
        width=int(camera["width"]), height=int(camera["height"]), fx=float(camera["fx"]), fy=float(camera["fy"]),
        cx=float(camera["cx"]), cy=float(camera["cy"]), depth_scale=float(camera.get("depth_scale", 5000.0)),
        depth_trunc=float(camera.get("depth_trunc", 4.0)),
    )
    association = config.get("association", {})
    if (args.dataset / "manifest.json").exists():
        dataset = load_phone_dataset(args.dataset)
    else:
        dataset = load_tum_dataset(
            args.dataset,
            intrinsics=intrinsics,
            max_rgb_depth_difference_s=float(association.get("max_rgb_depth_difference_s", 0.02)),
            max_pose_difference_s=float(association.get("max_pose_difference_s", 0.02)),
        )
    rclpy.init()
    node = DatasetPlayer(
        dataset, rate=max(args.rate, 1e-6), max_frames=args.max_frames, rgb_topic=args.rgb_topic,
        depth_topic=args.depth_topic, camera_info_topic=args.camera_info_topic, odom_topic=args.odom_topic,
    )
    try:
        while rclpy.ok() and not getattr(node, "_done", False):
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
