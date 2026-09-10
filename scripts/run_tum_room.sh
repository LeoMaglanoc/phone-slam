#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
docker compose build slam
docker compose run --rm slam bash -lc \
  'scripts/download_tum.sh room && python3 -m slam_pipeline.scripts.run_ground_truth \
   data/rgbd_dataset_freiburg1_room --config config/tum_fr1_room.yaml \
   --output outputs/tum_room'

