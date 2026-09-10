#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p data/phone_recordings
adb exec-out run-as com.example.offlineslam tar -cf - files/recordings \
  | tar -xf - --strip-components=2 -C data/phone_recordings
echo "Phone recordings copied to data/phone_recordings"
