# Goal

Build a complete offline 3D reconstruction pipeline that will eventually consume recordings from a Samsung Galaxy S24 FE.

The intended final pipeline is:

```text
Galaxy S24 FE
    │
    ├── RGB
    ├── ARCore Raw Depth
    ├── Raw Depth confidence
    ├── ARCore 6-DoF pose
    ├── camera intrinsics
    ├── timestamps
    └── IMU
            │
            ▼
       recorded dataset
            │
            ▼
Laptop / offline
    │
    ├── RTAB-Map
    │     ├── external ARCore odometry
    │     ├── loop closure
    │     └── pose-graph optimization
    │
    └── Open3D
          ├── TSDF fusion
          ├── point cloud
          └── triangle mesh
```

Do **not** start with Android.

First prove that the offline pipeline works end-to-end using the TUM RGB-D SLAM benchmark.

Do not report the task complete merely because the code compiles. Actually download the benchmark data, run the pipeline, inspect the outputs, and save evidence that it worked.

---

# 1. Technical choices

Use:

```text
Ubuntu
ROS 2 Jazzy
RTAB-Map / rtabmap_ros
Python 3
Open3D
NumPy
OpenCV
```

Prefer binary RTAB-Map packages first:

```bash
sudo apt install ros-jazzy-rtabmap-ros
```

RTAB-Map currently provides ROS 2 Jazzy packages, and its ROS wrapper explicitly allows external odometry to replace `rtabmap_odom`.

Use Docker only if native dependencies become problematic. Do not introduce Docker unnecessarily.

---

# 2. Repository structure

Create approximately:

```text
slam/
├── README.md
├── requirements.txt
├── config/
│   ├── tum_fr1_xyz.yaml
│   ├── tum_fr1_room.yaml
│   └── phone_default.yaml
│
├── scripts/
│   ├── setup.sh
│   ├── download_tum.sh
│   ├── run_tum_xyz.sh
│   ├── run_tum_room.sh
│   └── reconstruct.sh
│
├── src/
│   ├── dataset/
│   │   ├── schema.py
│   │   ├── tum_rgbd.py
│   │   └── phone_dataset.py
│   │
│   ├── ros/
│   │   ├── dataset_player.py
│   │   └── trajectory_export.py
│   │
│   ├── reconstruction/
│   │   ├── tsdf.py
│   │   ├── pointcloud.py
│   │   └── filters.py
│   │
│   └── evaluation/
│       ├── trajectory.py
│       └── validate_outputs.py
│
├── tests/
│   ├── test_tum_loader.py
│   ├── test_pose_conventions.py
│   ├── test_depth_conversion.py
│   └── test_tsdf_smoke.py
│
├── data/
│   └── .gitkeep
│
└── outputs/
    └── .gitkeep
```

Do not commit benchmark datasets or large generated meshes to Git.

---

# 3. Define one internal dataset format first

Everything downstream must use one sensor-recording abstraction independent of TUM or Android.

Represent a frame as conceptually:

```python
Frame:
    timestamp_ns
    rgb_path
    depth_path
    confidence_path | None
    T_world_camera
    intrinsics
```

A complete dataset also contains:

```text
camera intrinsics
camera image dimensions
depth scale
ordered RGB/depth observations
timestamp associations
optional IMU measurements
optional confidence maps
```

Use transformation notation consistently:

```text
T_world_camera
```

meaning a point in camera coordinates transforms into world coordinates as

```text
p_world = T_world_camera @ p_camera
```

Document this convention prominently.

Never silently invert poses.

---

# 4. Benchmark Gate A — TUM freiburg1_xyz

Download the official:

```text
rgbd_dataset_freiburg1_xyz
```

sequence from the TUM RGB-D SLAM benchmark.

TUM specifically recommends the `xyz` sequences for first experiments because the motion is simple and suitable for debugging.

The dataset contains timestamped:

```text
RGB PNGs
depth PNGs
RGB timestamps
depth timestamps
ground-truth trajectory
```

TUM depth PNG values use:

```text
depth_meters = uint16_value / 5000
```

and zero indicates invalid depth. RGB and depth are already registered pixel-to-pixel.

Ground-truth format is:

```text
timestamp tx ty tz qx qy qz qw
```

and describes the color camera pose with respect to a fixed world frame.

Implement a proper timestamp association instead of pairing files by array index.

---

# 5. First sanity reconstruction: ground truth → Open3D

Before RTAB-Map, prove basic geometry.

Use:

```text
TUM RGB
+
TUM depth
+
TUM ground-truth poses
+
camera intrinsics
        ↓
Open3D TSDF
        ↓
mesh + point cloud
```

Use `ScalableTSDFVolume` or the current equivalent suitable for scene-scale reconstruction.

Open3D's documented TSDF workflow integrates RGB-D images using known camera poses and then extracts a triangle mesh or point cloud.

Use the TUM-recommended default registered RGB-D calibration initially:

```text
fx = 525
fy = 525
cx = 319.5
cy = 239.5
```

because TUM warns that undistorting the already registered depth maps is non-trivial and recommends the default parameter set for this data.

Produce:

```text
outputs/tum_xyz/gt_tsdf_mesh.ply
outputs/tum_xyz/gt_pointcloud.ply
outputs/tum_xyz/gt_trajectory.png
outputs/tum_xyz/gt_mesh_preview.png
```

This stage must run before RTAB-Map integration.

Acceptance criteria:

```text
mesh file exists
mesh has > 0 vertices
mesh has > 0 triangles
point cloud has > 0 points
bounding box dimensions are finite and plausible
no NaNs/Infs in geometry
a preview image is rendered successfully
```

Print all counts and bounding-box dimensions to the terminal.

---

# 6. Build a ROS 2 offline dataset player

Create a ROS 2 node that publishes the normalized dataset as if it were a live RGB-D camera plus external odometry.

Publish:

```text
/rgb/image
/depth/image
/camera_info
/odom
/tf
```

Use dataset timestamps, not wall-clock timestamps.

Set ROS simulated time appropriately if useful.

For benchmark V1, use TUM ground truth as `/odom`.

This intentionally simulates the future phone architecture:

```text
TUM ground truth pose ≈ future ARCore pose
TUM RGB              ≈ future ARCore camera frame
TUM depth            ≈ future ARCore Raw Depth
```

RTAB-Map accepts external odometry rather than requiring its own RGB-D odometry node.

Do not run `rgbd_odometry` for this test.

---

# 7. RTAB-Map benchmark pipeline

Feed:

```text
RGB
depth
camera info
external /odom
```

into `rtabmap_slam`.

Pipeline:

```text
TUM dataset player
       │
       ├── RGB ──────────┐
       ├── depth ────────┤
       ├── camera_info ──┼── RTAB-Map
       └── GT odometry ──┘
                              │
                              ├── map database
                              ├── keyframes
                              ├── graph constraints
                              └── optimized poses
```

Disable RTAB-Map's visual odometry because external odometry is being supplied.

Make synchronization deterministic for offline replay.

Do not skip frames because the system is slower than playback. RTAB-Map's launch configuration explicitly exposes an option intended for dataset/offline processing so all frames can be processed instead of dropping frames to reduce latency.

Save:

```text
outputs/tum_xyz/rtabmap.db
outputs/tum_xyz/optimized_trajectory.txt
outputs/tum_xyz/rtabmap_stats.json
```

The stats file should include at least:

```text
number of processed RGB-D frames
number of graph nodes
number of constraints
number of loop closures if available
processing failures
runtime
```

---

# 8. Export RTAB-Map's optimized trajectory

Export the final camera poses after RTAB-Map graph optimization.

Convert them into the TUM trajectory format:

```text
timestamp tx ty tz qx qy qz qw
```

Save:

```text
outputs/tum_xyz/optimized_trajectory.txt
```

Plot three trajectories if available:

```text
TUM ground truth
input odometry
RTAB-Map optimized trajectory
```

For the first benchmark these may overlap closely because ground truth itself is being used as the odometry source.

That is expected.

The purpose of this test is initially **interface and reconstruction validation**, not demonstrating that RTAB-Map can improve motion-capture poses.

---

# 9. Final dense reconstruction from optimized poses

Now run:

```text
RGB-D frames
+
RTAB-Map optimized poses
        ↓
Open3D TSDF
        ↓
final point cloud + mesh
```

Generate:

```text
outputs/tum_xyz/final_mesh.ply
outputs/tum_xyz/final_cloud.ply
outputs/tum_xyz/final_mesh_preview.png
```

Open3D expects RGB and depth corresponding to the same camera geometry for its RGB-D reconstruction pipeline, which TUM provides by pre-registering its depth maps to RGB.

Make these configurable:

```text
voxel size
SDF truncation
minimum depth
maximum depth
frame stride
```

Do not aggressively tune them to one benchmark.

---

# 10. Quantitative trajectory evaluation

Use TUM's trajectory evaluation tools or an equivalent implementation.

Compute at least:

```text
ATE RMSE
ATE mean
ATE median
RPE translation
RPE rotation
```

TUM's benchmark explicitly supports absolute trajectory error for SLAM evaluation and relative pose error for odometry evaluation.

Save:

```text
outputs/tum_xyz/evaluation.json
outputs/tum_xyz/ate_plot.png
outputs/tum_xyz/trajectory_comparison.png
```

Do not invent a success threshold purely to make the test pass.

Instead report the measured result and confirm that:

```text
trajectory is finite
coordinate convention is correct
scale is correct
trajectory aligns visually with ground truth
there are no catastrophic jumps or axis inversions
```

---

# 11. Benchmark Gate B — freiburg1_room

After `freiburg1_xyz` works, automatically download and run:

```text
rgbd_dataset_freiburg1_room
```

This is the stronger integration test.

TUM describes this sequence as traversing an entire office and closing a loop, specifically making it useful for testing loop-closure behavior.

Repeat:

```text
dataset parsing
    ↓
ground-truth TSDF sanity reconstruction
    ↓
RTAB-Map with external odometry
    ↓
optimized poses
    ↓
Open3D TSDF
    ↓
mesh
    ↓
trajectory evaluation
```

Save all results under:

```text
outputs/tum_room/
```

Inspect RTAB-Map's statistics and report whether visual loop closures were detected.

Do not fake or require a loop-closure count if RTAB-Map genuinely does not detect one with the chosen configuration. Report the actual result and investigate if zero.

---

# 12. Automated end-to-end command

I want this eventually reduced to:

```bash
./scripts/run_tum_xyz.sh
```

and:

```bash
./scripts/run_tum_room.sh
```

Each command should:

```text
download dataset if missing
verify data
associate timestamps
launch/replay RTAB-Map
wait for processing to finish
export optimized poses
run TSDF integration
run evaluation
render previews
validate outputs
exit 0 only if the pipeline completed successfully
```

No manual RViz interaction may be required for the automated test.

RViz may be supported as an optional debugging mode.

---

# 13. Produce an HTML or Markdown run report

For each benchmark automatically generate:

```text
outputs/tum_xyz/report.md
outputs/tum_room/report.md
```

Include:

```text
dataset used
number of RGB frames
number of depth frames
number of associated frames
number of RTAB-Map graph nodes
number of loop closures
trajectory metrics
mesh vertex count
mesh triangle count
point count
scene bounding box
runtime
commands executed
warnings/errors
```

Embed or reference:

```text
trajectory plot
RGB example
depth example
mesh preview
```

The report must make it possible to inspect whether the run really worked without reading terminal logs.

---

# 14. Only after benchmark success: define the S24 FE format

Create the phone recording format:

```text
scan/
├── metadata.json
├── rgb/
│   ├── 000000.jpg
│   └── ...
├── depth/
│   ├── 000000.png
│   └── ...
├── confidence/
│   ├── 000000.png
│   └── ...
├── poses.csv
├── imu.csv
└── frames.csv
```

`metadata.json`:

```json
{
  "rgb_width": 0,
  "rgb_height": 0,
  "depth_width": 0,
  "depth_height": 0,
  "fx": 0,
  "fy": 0,
  "cx": 0,
  "cy": 0,
  "depth_unit": "millimeters",
  "pose_convention": "T_world_camera"
}
```

`frames.csv` should associate:

```text
frame_id
rgb_timestamp_ns
rgb_path
depth_timestamp_ns
depth_path
confidence_path
pose_timestamp_ns
```

`poses.csv`:

```text
timestamp_ns,tx,ty,tz,qx,qy,qz,qw
```

`imu.csv`:

```text
timestamp_ns,gx,gy,gz,ax,ay,az
```

IMU should be recorded now even though the V1 offline mapper does not consume it. This preserves the option to compare ARCore odometry with our own VIO later.

---

# 15. Important ARCore Raw Depth handling

The eventual Android recorder must save:

```text
RGB
ARCore camera pose
Raw Depth
Raw Depth confidence
depth timestamp
RGB/camera timestamp
camera intrinsics
IMU
```

Do not assume every rendered ARCore frame contains a newly computed Raw Depth map.

ARCore documents that Raw Depth is typically updated at a lower frequency and intermediate depth images can be reprojections of older data; compare the depth image timestamp to determine whether it contains a new measurement.

Therefore save the actual:

```text
depth_timestamp_ns
```

and add:

```text
is_new_depth
```

to `frames.csv`.

ARCore Raw Depth is sparse; invalid pixels have zero depth and zero confidence. The matching confidence image ranges from 0 to 255.

Do not fill missing depth with arbitrary interpolation in V1.

Treat zero as invalid.

Expose configurable confidence filtering, initially:

```text
minimum confidence
```

rather than hard-coding one threshold.

---

# 16. ARCore depth intrinsics/alignment

Do not assume the depth image has the same resolution as the RGB image.

ARCore depth resolution is device-dependent and can differ from the camera image. Google's example scales camera texture intrinsics to the depth-image dimensions before unprojection.

Implement the phone loader such that it can either:

```text
A. convert Raw Depth into RGB camera geometry

or

B. preserve depth-camera geometry with the appropriate intrinsics
```

Choose one convention and document it.

The downstream mapper must not silently pretend mismatched RGB/depth coordinates are registered.

---

# 17. Phone pipeline after the benchmark

Only after the TUM tests pass, implement:

```text
Android recorder
        ↓
copy scan folder to laptop
        ↓
python phone_dataset.py
        ↓
same normalized Frame abstraction used for TUM
        ↓
same RTAB-Map pipeline
        ↓
same Open3D TSDF pipeline
```

There should be no phone-specific logic in RTAB-Map or TSDF code.

Only the dataset adapter should differ:

```text
TUM adapter ────┐
                ▼
           common dataset
                ▲
Phone adapter ──┘
```

---

# 18. Confidence-aware reconstruction

Once basic phone reconstruction works, support an optional preprocessing stage:

```text
ARCore Raw Depth
        +
confidence
        ↓
mask unreliable pixels
        ↓
RTAB-Map / Open3D
```

ARCore's Raw Depth API exists specifically with a matching confidence image, and Google describes Raw Depth as the higher-accuracy but incomplete depth representation useful for geometry and reconstruction tasks.

Keep the unfiltered data.

Filtering should happen offline so we can rerun experiments with different thresholds without rescanning.

---

# 19. Explicitly out of scope for V1

Do not implement yet:

```text
stereo main + ultrawide
ORB-SLAM3
custom VIO
AnyDepth / neural monocular depth
Gaussian splatting
semantic mapping
real-time mesh reconstruction on phone
cloud processing
ROS navigation
```

The architecture should allow those later, but they must not delay the MVP.

---

# 20. Optional experiment after V1

Once the phone pipeline works, add interchangeable pose providers:

```text
PoseProvider
├── ARCorePoseProvider
├── ORBSLAM3PoseProvider
└── StereoVIOPoseProvider
```

and interchangeable depth providers:

```text
DepthProvider
├── ARCoreRawDepthProvider
├── StereoDepthProvider
└── LearnedDepthProvider
```

This lets us eventually compare:

```text
ARCore
vs
stereo
vs
learned depth
vs
hybrid fusion
```

without changing RTAB-Map or reconstruction code.

---

# 21. Tests

Implement unit tests for:

### Depth

Verify TUM conversion:

```text
5000 → 1.0 m
10000 → 2.0 m
0 → invalid
```

### Pose conversion

Create synthetic poses and confirm:

```text
T_world_camera
inverse(T_world_camera)
quaternion ↔ rotation matrix
```

round-trip correctly.

### Projection

Given:

```text
u, v, Z, fx, fy, cx, cy
```

verify:

```text
X = (u-cx)Z/fx
Y = (v-cy)Z/fy
```

and projection back to pixels.

### Timestamp association

Test:

```text
RGB timestamps
depth timestamps
pose timestamps
```

with missing and irregular samples.

### TSDF smoke test

Integrate a synthetic plane/cube and confirm non-empty output.

### Full benchmark integration

Run at least a shortened slice of `freiburg1_xyz` in CI if runtime permits.

The complete dataset test may remain a local integration test because benchmark data should not be committed to the repository.

---

# 22. Definition of done

The project is NOT complete until all of the following are true:

```text
[ ] TUM freiburg1_xyz downloaded automatically
[ ] Dataset parser works
[ ] RGB/depth/pose timestamps associated correctly
[ ] Ground-truth Open3D TSDF reconstruction succeeds
[ ] ROS2 dataset replay works
[ ] RTAB-Map accepts the externally supplied trajectory
[ ] RTAB-Map database contains map nodes
[ ] Optimized trajectory can be exported
[ ] Final Open3D TSDF reconstruction succeeds
[ ] .ply point cloud exists and is non-empty
[ ] .ply mesh exists and is non-empty
[ ] trajectory metrics are calculated
[ ] report.md is generated
[ ] mesh preview is generated
[ ] no hidden manual steps are required
[ ] freiburg1_room is run afterward
[ ] room reconstruction succeeds
[ ] actual loop-closure result is reported
[ ] README contains exact reproduction commands
```

---

# 23. Final response required from the agent

When finished, report:

```text
1. What was implemented.

2. Exact commands to reproduce it.

3. RTAB-Map and dependency versions actually used.

4. TUM sequences actually downloaded.

5. Number of benchmark frames successfully processed.

6. RTAB-Map nodes / constraints / loop closures.

7. ATE/RPE results.

8. Mesh:
   - vertices
   - triangles
   - bounding box.

9. Paths to:
   - rtabmap.db
   - optimized trajectory
   - point cloud
   - mesh
   - trajectory plots
   - mesh previews
   - report.md

10. Any warnings or remaining limitations.
```

Do not say “works” without providing these artifacts and measurements.

If anything fails, debug it and continue until either the benchmark works end-to-end or a concrete external blocker has been demonstrated with logs.

# Final architecture to preserve

```text
                 DATA ACQUISITION
                       │
       ┌───────────────┴────────────────┐
       │                                │
 TUM RGB-D                         S24 FE ARCore
benchmark adapter                    adapter
       │                                │
       └───────────────┬────────────────┘
                       ▼
              normalized dataset
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
        external pose       RGB + depth
              │                 │
              └────────┬────────┘
                       ▼
                    RTAB-Map
                       │
             optimized trajectory
                       │
                       ▼
                    Open3D
                       │
                  TSDF fusion
                       │
              ┌────────┴────────┐
              ▼                 ▼
         point cloud           mesh
```

Implement the benchmark side completely before beginning Android development.
