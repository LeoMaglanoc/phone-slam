#!/usr/bin/env bash
set -eo pipefail

sequence="${1:?usage: run_tum_benchmark_container.sh xyz|room}"
case "${sequence}" in
  xyz) dataset="data/rgbd_dataset_freiburg1_xyz"; config="config/tum_fr1_xyz.yaml"; output="outputs/tum_xyz" ;;
  room) dataset="data/rgbd_dataset_freiburg1_room"; config="config/tum_fr1_room.yaml"; output="outputs/tum_room" ;;
  *) echo "unknown TUM sequence: ${sequence}" >&2; exit 2 ;;
esac

# ROS Jazzy's setup script references optional variables, so enable nounset
# only after sourcing it.
source /opt/ros/jazzy/setup.bash
set -u
mkdir -p "${output}"
rm -f "${output}/rtabmap.db" "${output}/rtabmap.log" "${output}/replay_summary.json" "${output}/drain_summary.json" "${output}/graph_stats.json"
scripts/download_tum.sh "${sequence}"

python3 -m slam_pipeline.scripts.run_ground_truth "${dataset}" --config "${config}" --output "${output}/ground_truth"
python3 -m slam_pipeline.scripts.benchmark_examples "${dataset}" --config "${config}" --output "${output}/examples"

ros2 launch /workspace/scripts/rtabmap_tum.launch.py "database_path:=/workspace/${output}/rtabmap.db" > "${output}/rtabmap.log" 2>&1 &
rtabmap_launch_pid=$!

shutdown_rtabmap() {
  if kill -0 "${rtabmap_launch_pid}" 2>/dev/null; then
    kill -INT "${rtabmap_launch_pid}" 2>/dev/null || true
    for _ in $(seq 1 30); do
      if ! kill -0 "${rtabmap_launch_pid}" 2>/dev/null; then
        wait "${rtabmap_launch_pid}" 2>/dev/null || true
        return
      fi
      sleep 1
    done
    kill -TERM "${rtabmap_launch_pid}" 2>/dev/null || true
  fi
  wait "${rtabmap_launch_pid}" 2>/dev/null || true
}
trap shutdown_rtabmap EXIT

ready=0
for _ in $(seq 1 60); do
  if ros2 node list 2>/dev/null | grep -qx '/rtabmap'; then
    ready=1
    break
  fi
  sleep 0.5
done
if [[ "${ready}" != 1 ]]; then
  tail -n 120 "${output}/rtabmap.log" >&2 || true
  exit 1
fi

python3 -m slam_pipeline.ros.dataset_player "${dataset}" --config "${config}" --rate 1.0 --summary "${output}/replay_summary.json"
python3 -m slam_pipeline.scripts.wait_rtabmap "${output}/rtabmap.db" --stable-polls 5 --poll-s 1 --timeout-s 120 --output "${output}/drain_summary.json"
shutdown_rtabmap
trap - EXIT

python3 -m slam_pipeline.scripts.inspect_rtabmap "${output}/rtabmap.db" --output "${output}/graph_stats.json"
python3 -m slam_pipeline.scripts.evaluate_rtabmap "${dataset}" "${output}/rtabmap.db" --config "${config}" --output "${output}/evaluation"
python3 -m slam_pipeline.scripts.crosscheck_evo "${dataset}/groundtruth.txt" "${output}/evaluation/optimized_trajectory.txt" "${output}/evaluation/trajectory_metrics.json" --output "${output}/evaluation/evo_crosscheck.json"
python3 -m slam_pipeline.scripts.reconstruct_rtabmap "${dataset}" "${output}/rtabmap.db" --config "${config}" --output "${output}/optimized_tsdf"
python3 -m slam_pipeline.scripts.benchmark_report --sequence "${sequence}" --dataset "${dataset}" --output "${output}" --docs-output "docs/results/tum_${sequence}"
python3 -m slam_pipeline.scripts.validate_benchmark "${output}"
