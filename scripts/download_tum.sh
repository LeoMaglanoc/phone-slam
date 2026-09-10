#!/usr/bin/env bash
set -euo pipefail

sequence="${1:?usage: download_tum.sh xyz|room}"
case "$sequence" in
  xyz) name="rgbd_dataset_freiburg1_xyz" ;;
  room) name="rgbd_dataset_freiburg1_room" ;;
  *) echo "unknown sequence: $sequence" >&2; exit 2 ;;
esac

base="https://cvg.cit.tum.de/rgbd/dataset/freiburg1"
archive="data/${name}.tgz"
target="data/${name}"
mkdir -p data
if [[ ! -d "$target" ]]; then
  if [[ ! -f "$archive" ]]; then
    echo "Downloading ${name} (TUM official archive)"
    curl -fL --retry 3 --retry-delay 2 -o "$archive" "${base}/${name}.tgz"
  fi
  tar -xzf "$archive" -C data
fi
[[ -f "${target}/rgb.txt" ]] || { echo "invalid dataset: ${target}" >&2; exit 1; }
[[ -f "${target}/depth.txt" ]] || { echo "invalid dataset: ${target}" >&2; exit 1; }
[[ -f "${target}/groundtruth.txt" ]] || { echo "invalid dataset: ${target}" >&2; exit 1; }
echo "Dataset ready: ${target}"

