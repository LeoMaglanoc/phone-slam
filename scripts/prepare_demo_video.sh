#!/usr/bin/env bash
set -euo pipefail

sequence="${1:?usage: prepare_demo_video.sh freiburg3_long_office_household}"
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ "$sequence" == "freiburg3_long_office_household" ]] || { echo "No presentation-video source configured for $sequence" >&2; exit 2; }
dataset="data/rgbd_dataset_freiburg3_long_office_household"
avi="$dataset/rgb.avi"
public_dir="web/public/demos/$sequence"
mkdir -p "$dataset" "$public_dir"
if [[ ! -s "$avi" ]]; then
  curl -fL --retry 3 --retry-delay 2 -o "$avi" "https://cvg.cit.tum.de/rgbd/dataset/freiburg3/rgbd_dataset_freiburg3_long_office_household.avi"
fi
ffmpeg -y -i "$avi" -c:v libx264 -crf 20 -preset slow -pix_fmt yuv420p -movflags +faststart -an "$public_dir/demo.mp4"
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate -of json "$public_dir/demo.mp4" > "$public_dir/video_info.json"
echo "Prepared $public_dir/demo.mp4"
