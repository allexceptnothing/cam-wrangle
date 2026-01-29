import cv2
import time
import threading
import numpy as np
import json
import os
from colour import ColourPipeline, wb_multipliers_from_temp_tint
from ocio import OcioPipeline
from config import SETTINGS_FILE

# --- Settings Persistence ---

def save_settings(params):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(params, f, indent=4)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    # Defaults if file doesn't exist or is corrupt
    return {"temp": 0.0, "tint": 0.0, "gain": 1.0, "slope": 1.0, "power": 1.0}

# --- UI Management ---

def make_trackbar(window: str):
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.createTrackbar("Temp", window, 100, 200, lambda v: None)
    cv2.createTrackbar("Tint", window, 100, 200, lambda v: None)
    cv2.createTrackbar("Gain", window, 100, 400, lambda v: None)
    cv2.createTrackbar("Slope", window, 100, 300, lambda v: None) # 0.0 to 3.0
    cv2.createTrackbar("Power", window, 100, 300, lambda v: None) # 0.0 to 3.0

def read_sliders(window: str):
    return {
        "temp": (cv2.getTrackbarPos("Temp", window) - 100) / 100.0,
        "tint": (cv2.getTrackbarPos("Tint", window) - 100) / 100.0,
        "gain": cv2.getTrackbarPos("Gain", window) / 100.0,
        "slope": cv2.getTrackbarPos("Slope", window) / 100.0,
        "power": cv2.getTrackbarPos("Power", window) / 100.0
    }

def apply_settings_to_sliders(window, vals):
    cv2.setTrackbarPos("Temp", window, int(vals.get("temp", 0) * 100 + 100))
    cv2.setTrackbarPos("Tint", window, int(vals.get("tint", 0) * 100 + 100))
    cv2.setTrackbarPos("Gain", window, int(vals.get("gain", 1) * 100))
    cv2.setTrackbarPos("Slope", window, int(vals.get("slope", 1) * 100))
    cv2.setTrackbarPos("Power", window, int(vals.get("power", 1) * 100))

# --- Camera Threading ---

class CameraStream:
    def __init__(self, device, width, height):
        self.cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        self.ret, self.frame = False, None
        self.stopped = False
        self.new_frame_ready = False

    def start(self):
        threading.Thread(target=self.update, args=(), daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame
                self.ret = True
                self.new_frame_ready = True

    def read(self):
        self.new_frame_ready = False
        return self.ret, self.frame

    def stop(self):
        self.stopped = True
        self.cap.release()

# --- Main Preview Loop ---

def run_preview(config, timers=True):
    ocio_pipe = OcioPipeline(
        config.OCIO_CONFIG,
        config.OCIO_SPACES["input"],
        config.OCIO_SPACES["working"],
        config.OCIO_SPACES["display_device"],
        config.OCIO_SPACES["view"]
    )

    window = "Cam Wrangle"
    make_trackbar(window)

    initial_vals = load_settings()
    apply_settings_to_sliders(window, initial_vals)

    stream = CameraStream(config.CAMERA_DEVICE, 1920, 1080).start()

    # Initial frame wait to get dimensions
    while True:
        ret, frame = stream.read()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            break
        time.sleep(0.1)

    pipeline = ColourPipeline(config, w, h, ocio_pipe)
    last_params = {}

    if timers:
        t_read = t_proc = 0.0
        n_frames = 0
        last_time = time.perf_counter()

    print("Pipeline Active. 'q' to quit.")

    try:
        while True:
            if not stream.new_frame_ready:
                time.sleep(0.001)
                continue

            if timers: t0 = time.perf_counter()

            ret, frame = stream.read()

            if timers: t1 = time.perf_counter()

            if not ret or frame is None: continue

            # Slider check
            current_params = read_sliders(window)

            if current_params != last_params:
                r, g, b = wb_multipliers_from_temp_tint(
                    current_params["temp"],
                    current_params["tint"]
                )

                # Update LUT
                ocio_pipe.update_processor(
                    r, g, b,
                    current_params["gain"] * 4.5,
                    slope_val=current_params["slope"],
                    power_val=current_params["power"]
                )

                save_settings(current_params)
                last_params = current_params.copy()

            # Process image
            out = pipeline.process_bgr_u8(
                frame,
                current_params["temp"],
                current_params["tint"],
                current_params["gain"]
            )

            if timers: t2 = time.perf_counter()

            cv2.imshow(window, out)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            if timers:
                t_read += (t1 - t0)
                t_proc += (t2 - t1)
                n_frames += 1
                if n_frames % 60 == 0:
                    now = time.perf_counter()
                    fps = 60.0 / (now - last_time)
                    print(f"FPS {fps:.1f} | Read Latency: {1000*t_read/n_frames:.2f}ms | Proc: {1000*t_proc/n_frames:.1f}ms")
                    t_read = t_proc = 0.0
                    n_frames = 0
                    last_time = now

    finally:
        stream.stop()
        cv2.destroyAllWindows()
