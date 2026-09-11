# TUM freiburg3_long_office_household benchmark

## Environment

- git_sha: `c07d1eb6e1e3b56810c2a8ab2a878721e17ee812`
- date_utc: `2026-09-11T09:18:55.982832+00:00`
- python: `3.12.3`
- open3d: `0.19.0`
- ros: `jazzy`
- rtabmap: `unavailable (Command '('/opt/ros/jazzy/bin/rtabmap-export', '--version')' returned non-zero exit status 127.)`

## Dataset and association

- sequence: freiburg3_long_office_household
- source_url: https://cvg.cit.tum.de/data/datasets/rgbd-dataset

## RTAB-Map graph

- node_count: 481
- link_count: 745
- database_size_bytes: 221138944
- first_node_stamp: 1341847987.9977937
- last_node_stamp: 1341848067.826795
- neighbor_link_count: 480
- global_loop_closure_count: 90
- local_space_closure_count: 175
- local_time_closure_count: 0

## Trajectory metrics

### Raw Odometry

- associated_poses: 480
- ate_rmse_m: 0.061486127479072485
- ate_mean_m: 0.04805391334238589
- ate_median_m: 0.03338967257312215
- ate_max_m: 0.21078218205531918
- rpe_translation_rmse_m: 0.007570564759829535
- rpe_rotation_rmse_rad: 0.007302595593216812
- max_timestamp_residual_s: 0.00845479965209961
- mean_timestamp_residual_s: 0.002609137197335561

### Optimized

- associated_poses: 480
- ate_rmse_m: 0.04393297391421752
- ate_mean_m: 0.0374229449821231
- ate_median_m: 0.028940511072784954
- ate_max_m: 0.08212912638354788
- rpe_translation_rmse_m: 0.007152223104642492
- rpe_rotation_rmse_rad: 0.0077653544223558685
- max_timestamp_residual_s: 0.00845479965209961
- mean_timestamp_residual_s: 0.002609137197335561

## Independent evaluator cross-check

- evo_ape_rmse_m: 0.043933
- project_ate_rmse_m: 0.04393297391421752
- evo_rpe_translation_rmse_m: 0.007152
- project_rpe_translation_rmse_m: 0.007152223104642492
- evo_rpe_rotation_rmse_rad: 0.007765
- project_rpe_rotation_rmse_rad: 0.0077653544223558685
- ate_rmse_difference_m: 2.6085782478535435e-08
- rpe_translation_rmse_difference_m: 2.231046424914368e-07
- rpe_rotation_rmse_difference_rad: 3.5442235586831405e-07
- within_1e-5_tolerance: True
## TSDF

- mesh_vertices: 154488
- mesh_triangles: 241080
- point_count: 148989
- bounding_box_min: [-4.683681513238297, -2.685, -2.668246559594581]
- bounding_box_max: [5.036180861210455, 2.5901751384932172, 8.069334059708767]
- bounding_box_size: [9.719862374448752, 5.275175138493218, 10.737580619303348]
- integrated_frames: 240
- associated_frames: 480
- optimized_rtabmap_poses: 480
- unmatched_rtabmap_poses: 0
- max_timestamp_difference_s: 0.04292011260986328
- mean_timestamp_difference_s: 0.03176664809385935
- database: outputs/tum_long_office/rtabmap.db

## Replay and completion

- dataset: rgbd_dataset_freiburg3_long_office_household
- attempted_frames: 2488
- published_rgb_frames: 2488
- published_depth_frames: 2488
- published_odometry_poses: 0
- dropped_or_rejected_frames: 0
- start_timestamp_epoch_s: 1789117830.910717
- end_timestamp_epoch_s: 1789118059.3261654
- runtime_s: 228.4154485159961
- error: None
- database_quiescence: {'stable': True, 'stable_polls': 8, 'node_count': 481, 'elapsed_s': 8.010868049001147, 'database': {'node_count': 481, 'link_count': 745, 'database_size_bytes': 221138944, 'first_node_stamp': 1341847987.9977937, 'last_node_stamp': 1341848067.826795, 'neighbor_link_count': 480, 'global_loop_closure_count': 90, 'local_space_closure_count': 175, 'local_time_closure_count': 0}}

## Warnings / errors

- None reported by the benchmark orchestrator.
