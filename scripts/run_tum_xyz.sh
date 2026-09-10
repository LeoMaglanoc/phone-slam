#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
docker compose build slam
docker compose run --rm slam bash -lc \
  'scripts/download_tum.sh xyz && python3 -m slam_pipeline.scripts.run_ground_truth \
   data/rgbd_dataset_freiburg1_xyz --config config/tum_fr1_xyz.yaml \
   --output outputs/tum_fr1_xyz_gt'
