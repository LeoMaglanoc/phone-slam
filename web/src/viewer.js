import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { trajectoryObject } from "./trajectory.js";

export class MapViewer {
  constructor(canvas, loadingElement) {
    this.canvas = canvas;
    this.loadingElement = loadingElement;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0a1018);
    this.camera = new THREE.PerspectiveCamera(50, 1, 0.01, 1000);
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x22334a, 2.2));
    const key = new THREE.DirectionalLight(0xffffff, 1.6);
    key.position.set(4, 8, 3);
    this.scene.add(key);
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas.parentElement);
    this.resetPose = null;
    this.trajectory = null;
    this.animate();
  }

  async load(meshUrl, samples) {
    const loader = new GLTFLoader();
    const gltf = await loader.loadAsync(meshUrl);
    this.scene.add(gltf.scene);
    this.trajectory = trajectoryObject(samples);
    this.scene.add(this.trajectory);
    const box = new THREE.Box3().setFromObject(gltf.scene);
    box.expandByObject(this.trajectory);
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const distance = Math.max(sphere.radius * 2.4, 1.5);
    this.controls.target.copy(sphere.center);
    this.camera.position.set(sphere.center.x + distance, sphere.center.y + distance * 0.65, sphere.center.z + distance);
    this.camera.lookAt(sphere.center);
    this.controls.update();
    this.resetPose = { position: this.camera.position.clone(), target: this.controls.target.clone() };
    this.loadingElement.hidden = true;
    this.resize();
  }

  reset() {
    if (!this.resetPose) return;
    this.camera.position.copy(this.resetPose.position);
    this.controls.target.copy(this.resetPose.target);
    this.controls.update();
  }

  setTrajectoryVisible(visible) {
    if (this.trajectory) this.trajectory.visible = visible;
  }

  resize() {
    const { width, height } = this.canvas.parentElement.getBoundingClientRect();
    if (!width || !height) return;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
  }

  animate() {
    this.renderer.setAnimationLoop(() => {
      this.controls.update();
      this.renderer.render(this.scene, this.camera);
    });
  }
}
