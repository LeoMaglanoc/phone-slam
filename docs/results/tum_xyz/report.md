# TUM fr1/xyz benchmark

## Environment

- git_sha: `392b4ca5b3c937bd135c169b7d4c30c0a25159ac`
- date_utc: `2026-09-10T21:06:28.775936+00:00`
- python: `3.12.3`
- open3d: `0.19.0`
- ros: `jazzy`
- rtabmap: `unavailable ([Errno 2] No such file or directory: 'rtabmap-export')`

## Dataset and association

- sequence: fr1/xyz
- source_url: https://cvg.cit.tum.de/data/datasets/rgbd-dataset
- rgb_observations: 798
- depth_observations: 798
- pose_observations: 3000
- associated_rgb_depth_pairs: 794
- associated_rgb_depth_pose_triples: 792
- dropped_rgb_frames: 6

## RTAB-Map graph

- node_count: 203
- link_count: 527
- database_size_bytes: 87916544
- first_node_stamp: 1305031102.475318
- last_node_stamp: 1305031128.679282
- neighbor_link_count: 202
- global_loop_closure_count: 118
- local_space_closure_count: 207
- local_time_closure_count: 0

## Trajectory metrics

### Raw Odometry

- associated_poses: 202
- ate_rmse_m: 2.2255927286015834e-16
- ate_mean_m: 1.8337315717179569e-16
- ate_median_m: 2.220446049250313e-16
- ate_max_m: 3.8459253727671276e-16
- rpe_translation_rmse_m: 3.602448825026074e-08
- rpe_rotation_rmse_rad: 1.4063276119281752e-06
- max_timestamp_residual_s: 0.004936933517456055
- mean_timestamp_residual_s: 0.002920982861282802

### Optimized

- associated_poses: 202
- ate_rmse_m: 0.004714898273388859
- ate_mean_m: 0.004355372557349483
- ate_median_m: 0.004530134657081769
- ate_max_m: 0.012688036389530215
- rpe_translation_rmse_m: 0.0004009467277341939
- rpe_rotation_rmse_rad: 0.00010575820514529481
- max_timestamp_residual_s: 0.004936933517456055
- mean_timestamp_residual_s: 0.002920982861282802

## Independent evaluator cross-check

- evo_ape_rmse_m: 0.004715
- project_ate_rmse_m: 0.004714898273388859
- evo_rpe_translation_rmse_m: 0.000401
- project_rpe_translation_rmse_m: 0.0004009467277341939
- evo_rpe_rotation_rmse_rad: 0.000106
- project_rpe_rotation_rmse_rad: 0.00010575820514529481
- ate_rmse_difference_m: 1.0172661114079412e-07
- rpe_translation_rmse_difference_m: 5.327226580611327e-08
- rpe_rotation_rmse_difference_rad: 2.4179485470519403e-07
- within_1e-5_tolerance: True
## TSDF

- mesh_vertices: 29142
- mesh_triangles: 46499
- point_count: 28236
- bounding_box_min: [-2.565, -2.235, -0.20682973262029442]
- bounding_box_max: [1.305, 2.5348598448081296, 1.4249999999999998]
- bounding_box_size: [3.87, 4.7698598448081295, 1.6318297326202942]
- integrated_frames: 202
- associated_frames: 202
- optimized_rtabmap_poses: 202
- unmatched_rtabmap_poses: 0
- max_timestamp_difference_s: 0.039817094802856445
- mean_timestamp_difference_s: 0.033388906186169916
- database: outputs/tum_xyz/rtabmap.db

## Replay and completion

- dataset: rgbd_dataset_freiburg1_xyz
- attempted_frames: 792
- published_rgb_frames: 792
- published_depth_frames: 792
- published_odometry_poses: 792
- dropped_or_rejected_frames: 0
- start_timestamp_epoch_s: 1789073942.4814649
- end_timestamp_epoch_s: 1789074013.575715
- runtime_s: 71.09424969300017
- error: None
- database_quiescence: {'stable': True, 'stable_polls': 5, 'node_count': 203, 'elapsed_s': 5.005964388999928, 'database': {'node_count': 203, 'link_count': 527, 'database_size_bytes': 87916544, 'first_node_stamp': 1305031102.475318, 'last_node_stamp': 1305031128.679282, 'neighbor_link_count': 202, 'global_loop_closure_count': 118, 'local_space_closure_count': 207, 'local_time_closure_count': 0}}

## Warnings / errors

- None reported by the benchmark orchestrator.
