#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p outputs/tum_fr1_rtabmap
docker compose build slam
docker compose run --rm slam bash -lc '
  set -eo pipefail
  source /opt/ros/jazzy/setup.bash
  set -u
  rm -f outputs/tum_fr1_rtabmap/rtabmap.db
  stdbuf -o L ros2 launch /workspace/scripts/rtabmap_tum.launch.py \
    > outputs/tum_fr1_rtabmap/rtabmap.log 2>&1 &
  rtabmap_launch_pid=$!
  cleanup() {
    kill -INT "${rtabmap_launch_pid}" 2>/dev/null || true
    sleep 5
    kill -TERM "${rtabmap_launch_pid}" 2>/dev/null || true
    sleep 2
    kill -KILL "${rtabmap_launch_pid}" 2>/dev/null || true
    wait "${rtabmap_launch_pid}" 2>/dev/null || true
  }
  trap cleanup EXIT
  sleep 5
  python3 -m slam_pipeline.ros.dataset_player \
    data/rgbd_dataset_freiburg1_xyz --config config/tum_fr1_xyz.yaml --rate 1.0
  sleep 3
  cleanup
  trap - EXIT
  test -s outputs/tum_fr1_rtabmap/rtabmap.db
  echo "RTAB-Map database ready: outputs/tum_fr1_rtabmap/rtabmap.db"
'
