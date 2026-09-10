# Offline RGB-D SLAM and reconstruction

This repository is being built in gates. The first gate uses the official TUM
RGB-D benchmark and known ground-truth poses. Android acquisition is deliberately
deferred until the offline pipeline is proven.

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
./scripts/run_rtabmap_tum_xyz.sh
./scripts/build_android.sh
./scripts/install_android.sh
```

The Android prototype records RGB JPEGs, ARCore raw depth (`uint16` millimeter
binary), confidence maps, calibrated intrinsics, timestamps, and ARCore 6-DoF
poses in the `offline-slam-phone-v1` format. After unlocking the phone and
performing a scan, copy recordings with `./scripts/pull_phone_recordings.sh`;
then process one with:

```bash
docker compose run --rm slam python3 -m slam_pipeline.scripts.reconstruct_phone \
  data/phone_recordings/recording_YYYYMMDD_HHMMSS --output outputs/phone_scan
```

The phone recorder deliberately uses one logical RGB camera plus ARCore raw
depth and pose. Multi-camera stereo is out of scope for this pipeline.

TUM archives and generated geometry are ignored by Git.
