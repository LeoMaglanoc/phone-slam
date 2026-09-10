# Offline RGB-D SLAM and reconstruction

This repository implements an offline RGB-D mapping pipeline:

```text
TUM RGB-D or S24 FE / ARCore recording
  -> normalized RGB-D + pose dataset
  -> RTAB-Map external odometry and graph optimization
  -> optimized camera poses
  -> Open3D TSDF point cloud and mesh
```

## Pose convention

Every internal pose is `T_world_camera`: camera-coordinate points are transformed
to world coordinates with `p_world = T_world_camera @ p_camera`. Open3D receives
the inverse because its integration API expects world-to-camera extrinsics.

## Reproducible environment

The project uses Docker for ROS 2 Jazzy, RTAB-Map, and Python dependencies. The
workspace is mounted into the container, so datasets and generated artifacts
remain in `data/` and `outputs/` on the host.

```bash
./scripts/setup.sh
./scripts/run_tum_xyz.sh
./scripts/run_tum_room.sh
./scripts/test_benchmarks.sh
./scripts/build_android.sh
```

`run_tum_xyz.sh` and `run_tum_room.sh` are complete gates: download, one-to-one
association, ground-truth TSDF baseline, ROS replay, graph inspection, official
`rtabmap-export --opt 0`, raw/optimized ATE/RPE, `evo` cross-check, optimized
TSDF, validation, and small evidence under `docs/results/`.

## Android recording

The recorder writes `offline-slam-phone-v2`: native ARCore Raw Depth (`uint16`
little-endian millimetres), confidence, per-frame CPU-RGB and depth intrinsics,
per-frame texture-to-CPU-image coordinate mapping, asynchronous timestamps,
ARCore poses, and accelerometer/gyroscope samples. JPEG encoding and disk writes
run on a bounded background queue; its session summary reports missed, skipped,
dropped, and unexpected-error counts.

USB ADB stays on the host while the APK build remains Dockerized:

```bash
./scripts/build_android.sh
./scripts/install_android.sh
./scripts/pull_phone_recordings.sh
```

Process a recording directly from ARCore poses with:

```bash
docker compose run --rm slam python3 -m slam_pipeline.scripts.reconstruct_phone \
  data/phone_recordings/recording_YYYYMMDD_HHMMSS \
  --config config/phone_default.yaml --output outputs/phone_scan
```

Then replay the same recording through RTAB-Map with:

```bash
./scripts/run_phone_rtabmap.sh data/phone_recordings/recording_YYYYMMDD_HHMMSS
```

V2 does not resize raw depth to CPU RGB dimensions. It projects CPU RGB onto
the native depth grid using the coordinate mapping recorded from ARCore and
integrates using texture-derived depth intrinsics.

The phone recorder deliberately uses one logical RGB camera plus ARCore raw
depth and pose. Multi-camera stereo is out of scope for this pipeline.

TUM archives, phone recordings, databases, APKs, and generated geometry are
ignored by Git. Small benchmark reports, JSON metrics, and preview PNGs are
kept in `docs/results/`.
