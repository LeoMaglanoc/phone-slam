import numpy as np


def tum_depth_to_meters(values: np.ndarray) -> np.ndarray:
    depth = values.astype(np.float32) / 5000.0
    depth[values == 0] = 0.0
    return depth


def test_tum_depth_scale_and_invalid_zero() -> None:
    converted = tum_depth_to_meters(np.array([5000, 10000, 0], dtype=np.uint16))
    assert np.allclose(converted, [1.0, 2.0, 0.0])

