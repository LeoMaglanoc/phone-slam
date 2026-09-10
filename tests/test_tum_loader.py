from pathlib import Path

import cv2
import numpy as np

from slam_pipeline.dataset.tum_rgbd import load_tum_dataset


def test_tum_loader_associates_irregular_timestamps(tmp_path: Path) -> None:
    (tmp_path / "rgb").mkdir()
    (tmp_path / "depth").mkdir()
    cv2.imwrite(str(tmp_path / "rgb" / "0.png"), np.zeros((2, 2, 3), np.uint8))
    cv2.imwrite(str(tmp_path / "depth" / "0.png"), np.ones((2, 2), np.uint16))
    (tmp_path / "rgb.txt").write_text("# rgb\n1.000 image\n".replace("image", "rgb/0.png"))
    (tmp_path / "depth.txt").write_text("# depth\n1.008 depth/0.png\n")
    (tmp_path / "groundtruth.txt").write_text("1.004 0 0 0 0 0 0 1\n")
    dataset = load_tum_dataset(tmp_path, max_rgb_depth_difference_s=0.02, max_pose_difference_s=0.02)
    assert len(dataset.frames) == 1
    assert dataset.frames[0].depth_timestamp_ns == 1008000000

