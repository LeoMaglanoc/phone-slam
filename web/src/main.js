import "../styles/main.css";
import { MapViewer } from "./viewer.js";

const DEMOS = {
  freiburg3_long_office_household: "demos/freiburg3_long_office_household/metadata.json",
};
const root = import.meta.env.BASE_URL;
const name = new URLSearchParams(window.location.search).get("demo") || "freiburg3_long_office_household";
const metadataUrl = new URL(DEMOS[name] || DEMOS.freiburg3_long_office_household, new URL(root, window.location.origin));
const viewerElement = document.querySelector("#viewer");
const loading = document.querySelector("#loading");
const video = document.querySelector("#demo-video");
let trajectoryVisible = true;

function asset(metadata, key) {
  return new URL(`demos/${metadata.dataset.name}/${metadata.assets[key]}`, new URL(root, window.location.origin)).href;
}

function setMode(mode) {
  viewerElement.className = `viewer mode-${mode}`;
  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === mode);
    button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
  });
  window.dispatchEvent(new Event("resize"));
}

async function main() {
  try {
    const response = await fetch(metadataUrl);
    if (!response.ok) throw new Error(`Metadata request failed (${response.status})`);
    const metadata = await response.json();
    document.querySelector("#demo-title").textContent = metadata.title;
    document.querySelector("#demo-summary").textContent = "Estimated RGB-D odometry → RTAB-Map loop closure → optimized colored TSDF mesh.";
    document.querySelector("#dataset-link").href = metadata.dataset.url;
    document.querySelector("#stats").textContent = `${metadata.slam.input_frames.toLocaleString()} RGB-D frames · ${metadata.slam.graph_nodes.toLocaleString()} graph nodes · ${metadata.slam.global_loop_closures} global loop closures · ${metadata.mesh.triangles.toLocaleString()} web-mesh triangles`;
    video.src = asset(metadata, "video");
    const trajectoryResponse = await fetch(asset(metadata, "trajectory"));
    if (!trajectoryResponse.ok) throw new Error(`Trajectory request failed (${trajectoryResponse.status})`);
    const trajectory = await trajectoryResponse.json();
    const map = new MapViewer(document.querySelector("#map-canvas"), loading);
    await map.load(asset(metadata, "mesh"), trajectory.samples);
    document.querySelector("#reset-view").addEventListener("click", () => map.reset());
    document.querySelector("#trajectory-toggle").addEventListener("click", (event) => {
      trajectoryVisible = !trajectoryVisible;
      map.setTrajectoryVisible(trajectoryVisible);
      event.currentTarget.textContent = `Trajectory: ${trajectoryVisible ? "on" : "off"}`;
      event.currentTarget.setAttribute("aria-pressed", String(trajectoryVisible));
    });
  } catch (error) {
    loading.textContent = `Viewer failed to load: ${error.message}`;
    loading.classList.add("error");
    console.error(error);
  }
}

document.querySelectorAll("[data-mode]").forEach((button) => button.addEventListener("click", () => setMode(button.dataset.mode)));
document.querySelector("#fullscreen").addEventListener("click", async () => {
  if (document.fullscreenElement) await document.exitFullscreen();
  else await viewerElement.requestFullscreen();
});
main();
