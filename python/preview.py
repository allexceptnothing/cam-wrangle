import cv2
import time

from colour import OcioPipeline
from colour import ColourPipeline


def make_trackbar(window: str):
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)


    cv2.createTrackbar("Temp", window, 100, 200, lambda v: None)
    cv2.createTrackbar("Tint", window, 100, 200, lambda v: None)
    cv2.createTrackbar("Gain", window, 100, 400, lambda v: None)

def read_sliders(window: str):
    t = cv2.getTrackbarPos("Temp", window)
    n = cv2.getTrackbarPos("Tint", window)
    g = cv2.getTrackbarPos("Gain", window)

    temp = (t - 100) / 100.0
    tint = (n - 100) / 100.0
    gain = g / 100.0

    return temp, tint, gain


def run_preview(config, timers=True):

    ocio_pipeline = OcioPipeline(
        config.OCIO_CONFIG,
        config.OCIO_SPACES["input"],
        config.OCIO_SPACES["working"],
        config.OCIO_SPACES["display"],
    )

    window = "Cam Wrangle"
    make_trackbar(window)

    device = config.CAMERA_DEVICE
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {device}")

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv2.CAP_PROP_FPS, 30)

    def fourcc_str(v):
        v = int(v)
        return "".join([chr((v >> 8*i) & 0xFF) for i in range(4)])

    print("FOURCC:", fourcc_str(cap.get(cv2.CAP_PROP_FOURCC)))
    print("WxH:", cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print("FPS:", cap.get(cv2.CAP_PROP_FPS))

    ret, frame = cap.read()
    if not ret:
        raise RuntimeError("Could not read first frame")
    h, w = frame.shape[:2]

    pipeline = ColourPipeline(w, h, ocio_pipeline)

    cv2.namedWindow(window, cv2.WINDOW_NORMAL)


    if timers:
        t_read = t_proc = t_show = 0.0
        n = 0
        last = time.perf_counter()

    while True:

        if timers:
            t0 = time.perf_counter()


        ret, frame = cap.read()

        if timers:
            t1 = time.perf_counter()

        if not ret:
            break

        temp, tint, gain = read_sliders(window)
        out = pipeline.process_bgr_u8(frame, temp, tint, gain)

        if timers:
            t2 = time.perf_counter()

        cv2.imshow(window, out)
        cv2.waitKey(1)

        if timers:
            t3 = time.perf_counter()
            t_read += (t1 - t0)
            t_proc += (t2 - t1)
            t_show += (t3 - t2)
            n += 1
            if n % 60 == 0:
                now = time.perf_counter()
                fps = 60.0 / (now - last)
                last = now
                print(f"FPS {fps:.1f} | read {1000*t_read/n:.1f}ms | proc {1000*t_proc/n:.1f}ms | show {1000*t_show/n:.1f}ms")

    cap.release()
    cv2.destroyAllWindows()
