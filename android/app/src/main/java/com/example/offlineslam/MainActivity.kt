package com.example.offlineslam

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.graphics.ImageFormat
import android.graphics.Rect
import android.media.Image
import android.opengl.GLES11Ext
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.os.Bundle
import android.view.Gravity
import android.view.Surface
import android.widget.Button
import android.widget.FrameLayout
import android.widget.TextView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.ar.core.ArCoreApk
import com.google.ar.core.Config
import com.google.ar.core.Frame
import com.google.ar.core.Session
import com.google.ar.core.TrackingState
import java.io.BufferedWriter
import java.io.File
import java.io.FileOutputStream
import java.io.OutputStreamWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10
import kotlin.math.sqrt

class MainActivity : Activity() {
    private lateinit var glView: GLSurfaceView
    private lateinit var status: TextView
    private lateinit var button: Button
    private var session: Session? = null
    private var recorder: RecordingWriter? = null
    private var renderer: ArRenderer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), 10)
            return
        }
        initialize()
    }

    private fun initialize() {
        try {
            if (ArCoreApk.getInstance().requestInstall(this, true) == ArCoreApk.InstallStatus.INSTALL_REQUESTED) return
            session = Session(this)
            val config = Config(session).apply {
                updateMode = Config.UpdateMode.LATEST_CAMERA_IMAGE
                depthMode = if (session!!.isDepthModeSupported(Config.DepthMode.RAW_DEPTH_ONLY)) {
                    Config.DepthMode.RAW_DEPTH_ONLY
                } else {
                    Config.DepthMode.DISABLED
                }
            }
            session!!.configure(config)
        } catch (error: Exception) {
            setContentView(TextView(this).apply { text = "ARCore initialization failed: ${error.message}" })
            return
        }

        status = TextView(this).apply {
            text = "Ready. Depth support: ${session!!.isDepthModeSupported(Config.DepthMode.RAW_DEPTH_ONLY)}"
            setTextColor(0xFFFFFFFF.toInt())
            setBackgroundColor(0x99000000.toInt())
            setPadding(24, 18, 24, 18)
        }
        button = Button(this).apply {
            text = "Start recording"
            setOnClickListener { toggleRecording() }
        }
        glView = GLSurfaceView(this).apply {
            setEGLContextClientVersion(2)
            renderer = ArRenderer()
            setRenderer(renderer)
            renderMode = GLSurfaceView.RENDERMODE_CONTINUOUSLY
        }
        val layout = FrameLayout(this)
        layout.addView(glView)
        layout.addView(status, FrameLayout.LayoutParams(-2, -2).apply { gravity = Gravity.TOP or Gravity.START })
        layout.addView(button, FrameLayout.LayoutParams(-2, -2).apply { gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL })
        setContentView(layout)
    }

    private fun toggleRecording() {
        if (recorder == null) {
            recorder = RecordingWriter(File(filesDir, "recordings"))
            button.text = "Stop recording"
            status.text = "Recording…"
        } else {
            val directory = recorder!!.finish()
            recorder = null
            button.text = "Start recording"
            status.text = "Saved ${directory.name} (${directory.absolutePath})"
        }
    }

    override fun onResume() {
        super.onResume()
        if (::glView.isInitialized) {
            session?.resume()
            glView.onResume()
        }
    }

    override fun onPause() {
        if (::glView.isInitialized) glView.onPause()
        session?.pause()
        super.onPause()
    }

    override fun onDestroy() {
        recorder?.finish()
        session?.close()
        super.onDestroy()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 10 && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) initialize()
    }

    private inner class ArRenderer : GLSurfaceView.Renderer {
        private var cameraTexture = 0

        override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
            val textures = IntArray(1)
            GLES20.glGenTextures(1, textures, 0)
            cameraTexture = textures[0]
            GLES20.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, cameraTexture)
            GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_LINEAR)
            GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_LINEAR)
            session?.setCameraTextureName(cameraTexture)
        }

        override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) {
            GLES20.glViewport(0, 0, width, height)
            session?.setDisplayGeometry(Surface.ROTATION_0, width, height)
        }

        override fun onDrawFrame(gl: GL10?) {
            val currentSession = session ?: return
            val frame = try { currentSession.update() } catch (_: Exception) { return }
            GLES20.glClearColor(0f, 0f, 0f, 1f)
            GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT)
            if (frame.camera.trackingState == TrackingState.TRACKING) recorder?.record(frame)
        }
    }
}

private class RecordingWriter(private val root: File) {
    private val directory: File = File(root, "recording_" + SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date()))
    private val rgbDir = File(directory, "rgb")
    private val depthDir = File(directory, "depth")
    private val confidenceDir = File(directory, "confidence")
    private val frames: BufferedWriter
    private val poses: BufferedWriter
    private var frameIndex = 0
    private var manifestWritten = false

    init {
        rgbDir.mkdirs(); depthDir.mkdirs(); confidenceDir.mkdirs()
        frames = BufferedWriter(OutputStreamWriter(FileOutputStream(File(directory, "frames.csv"))))
        poses = BufferedWriter(OutputStreamWriter(FileOutputStream(File(directory, "poses.csv"))))
        frames.write("timestamp_ns,rgb_path,depth_path,confidence_path,depth_timestamp_ns\n")
        poses.write("timestamp_ns,tx,ty,tz,qx,qy,qz,qw,tracking_state\n")
    }

    fun record(frame: Frame) {
        var rgb: Image? = null
        var depth: Image? = null
        var confidence: Image? = null
        try {
            rgb = frame.acquireCameraImage()
            depth = frame.acquireRawDepthImage16Bits()
            confidence = frame.acquireRawDepthConfidenceImage()
            if (frame.timestamp != depth.timestamp) return
            val stem = "%09d".format(Locale.US, frameIndex++)
            writeJpeg(rgb, File(rgbDir, "$stem.jpg"))
            writePlane(depth, File(depthDir, "$stem.bin"), 2)
            writePlane(confidence, File(confidenceDir, "$stem.bin"), 1)
            val pose = convertedPose(frame)
            val q = matrixToQuaternion(pose)
            val t = frame.camera.pose.translation
            poses.write("${frame.timestamp},${t[0]},${t[1]},${t[2]},${q[0]},${q[1]},${q[2]},${q[3]},TRACKING\n")
            frames.write("${frame.timestamp},rgb/$stem.jpg,depth/$stem.bin,confidence/$stem.bin,${depth.timestamp}\n")
            if (!manifestWritten) {
                val intrinsics = frame.camera.imageIntrinsics
                val dimensions = intrinsics.imageDimensions
                val focal = intrinsics.focalLength
                val principal = intrinsics.principalPoint
                val depthDims = intArrayOf(depth.width, depth.height)
                File(directory, "manifest.json").writeText(
                    """{"format":"offline-slam-phone-v1","pose_convention":"T_world_camera","pose_camera_axes":"x_right_y_down_z_forward","depth_encoding":"uint16_little_endian_millimeters","depth_scale":0.001,"rgb_width":${dimensions[0]},"rgb_height":${dimensions[1]},"depth_width":${depthDims[0]},"depth_height":${depthDims[1]},"fx":${focal[0]},"fy":${focal[1]},"cx":${principal[0]},"cy":${principal[1]},"confidence_encoding":"uint8"}""".trimIndent()
                )
                manifestWritten = true
            }
            frames.flush(); poses.flush()
        } catch (_: Exception) {
            // A raw-depth frame is not guaranteed to be available for every ARCore frame.
        } finally {
            rgb?.close(); depth?.close(); confidence?.close()
        }
    }

    fun finish(): File {
        frames.flush(); poses.flush(); frames.close(); poses.close()
        return directory
    }

    private fun writeJpeg(image: Image, file: File) {
        val nv21 = yuv420ToNv21(image)
        FileOutputStream(file).use { output ->
            android.graphics.YuvImage(nv21, ImageFormat.NV21, image.width, image.height, null)
                .compressToJpeg(Rect(0, 0, image.width, image.height), 90, output)
        }
    }

    private fun writePlane(image: Image, file: File, bytesPerPixel: Int) {
        val plane = image.planes[0]
        val buffer = plane.buffer.duplicate()
        val rowBytes = image.width * bytesPerPixel
        FileOutputStream(file).use { output ->
            val row = ByteArray(rowBytes)
            for (y in 0 until image.height) {
                buffer.position(y * plane.rowStride)
                buffer.get(row, 0, rowBytes)
                output.write(row)
            }
        }
    }

    private fun yuv420ToNv21(image: Image): ByteArray {
        val width = image.width; val height = image.height
        val out = ByteArray(width * height * 3 / 2)
        copyPlane(image.planes[0], width, height, 1, out, 0)
        val u = image.planes[1]; val v = image.planes[2]
        var index = width * height
        val ub = u.buffer.duplicate(); val vb = v.buffer.duplicate()
        for (y in 0 until height / 2) {
            for (x in 0 until width / 2) {
                val offset = y * u.rowStride + x * u.pixelStride
                out[index++] = vb.get(offset)
                out[index++] = ub.get(offset)
            }
        }
        return out
    }

    private fun copyPlane(plane: Image.Plane, width: Int, height: Int, bytesPerPixel: Int, out: ByteArray, start: Int) {
        val buffer = plane.buffer.duplicate(); var index = start
        for (y in 0 until height) {
            for (x in 0 until width) {
                out[index++] = buffer.get(y * plane.rowStride + x * plane.pixelStride)
            }
        }
    }

    private fun convertedPose(frame: Frame): FloatArray {
        val ar = FloatArray(16)
        frame.camera.pose.toMatrix(ar, 0)
        // ARCore uses OpenGL camera axes (+X right, +Y up, -Z forward). Convert
        // to the pinhole/depth axes used by the offline pipeline (+X right,
        // +Y down, +Z forward) without inverting the world-camera pose.
        val rowMajor = FloatArray(16)
        for (row in 0..3) for (column in 0..3) rowMajor[row * 4 + column] = ar[column * 4 + row]
        val converted = rowMajor.copyOf()
        for (row in 0..2) {
            converted[row * 4 + 1] = -rowMajor[row * 4 + 1]
            converted[row * 4 + 2] = -rowMajor[row * 4 + 2]
        }
        return converted
    }

    private fun matrixToQuaternion(matrix: FloatArray): FloatArray {
        val trace = matrix[0] + matrix[5] + matrix[10]
        val q = FloatArray(4)
        if (trace > 0f) {
            val s = sqrt(trace + 1f) * 2f
            q[3] = 0.25f * s; q[0] = (matrix[9] - matrix[6]) / s; q[1] = (matrix[2] - matrix[8]) / s; q[2] = (matrix[4] - matrix[1]) / s
        } else if (matrix[0] > matrix[5] && matrix[0] > matrix[10]) {
            val s = sqrt(1f + matrix[0] - matrix[5] - matrix[10]) * 2f
            q[3] = (matrix[9] - matrix[6]) / s; q[0] = 0.25f * s; q[1] = (matrix[1] + matrix[4]) / s; q[2] = (matrix[2] + matrix[8]) / s
        } else if (matrix[5] > matrix[10]) {
            val s = sqrt(1f + matrix[5] - matrix[0] - matrix[10]) * 2f
            q[3] = (matrix[2] - matrix[8]) / s; q[0] = (matrix[1] + matrix[4]) / s; q[1] = 0.25f * s; q[2] = (matrix[6] + matrix[9]) / s
        } else {
            val s = sqrt(1f + matrix[10] - matrix[0] - matrix[5]) * 2f
            q[3] = (matrix[4] - matrix[1]) / s; q[0] = (matrix[2] + matrix[8]) / s; q[1] = (matrix[6] + matrix[9]) / s; q[2] = 0.25f * s
        }
        return q
    }
}
