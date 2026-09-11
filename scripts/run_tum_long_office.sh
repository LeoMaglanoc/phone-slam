#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
# Dataset/video retrieval uses the host's pre-existing curl/ffmpeg because this
# Docker network is intentionally isolated. Robotics computation remains in
# the reproducible `slam` container below.
./scripts/download_tum.sh freiburg3_long_office_household
./scripts/prepare_demo_video.sh freiburg3_long_office_household
exec docker compose run --rm slam bash /workspace/scripts/run_tum_long_office_container.sh
