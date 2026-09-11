import { readFile, stat } from "node:fs/promises";
import path from "node:path";

const root = path.resolve("public/demos/freiburg3_long_office_household");
const required = ["demo.mp4", "scene.glb", "trajectory.json", "metadata.json", "thumbnail.webp", "attribution.txt"];
for (const name of required) {
  const info = await stat(path.join(root, name));
  if (!info.isFile() || info.size === 0) throw new Error(`Missing or empty demo asset: ${name}`);
}
const metadata = JSON.parse(await readFile(path.join(root, "metadata.json"), "utf8"));
const trajectory = JSON.parse(await readFile(path.join(root, "trajectory.json"), "utf8"));
if (!Array.isArray(trajectory.samples) || trajectory.samples.length < 2) throw new Error("Invalid trajectory samples");
function finite(value) {
  if (Array.isArray(value)) return value.every(finite);
  if (value && typeof value === "object") return Object.values(value).every(finite);
  return typeof value !== "number" || Number.isFinite(value);
}
if (!finite(trajectory) || !finite(metadata)) throw new Error("Demo JSON has non-finite values");
for (const asset of Object.values(metadata.assets)) await stat(path.join(root, asset));
console.log(`Validated ${trajectory.samples.length} trajectory samples and browser assets.`);
