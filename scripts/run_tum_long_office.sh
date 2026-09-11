#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
docker compose build slam
exec docker compose run --rm slam bash /workspace/scripts/run_tum_long_office_container.sh
