import os

CURRENT_FILE = os.path.realpath(__file__)
DIR_PATH = os.path.dirname(CURRENT_FILE)
ROOT_PATH = os.path.abspath(os.path.join(DIR_PATH, ".."))
DATA_PATH = os.path.join(ROOT_PATH, "data")
PYTHON_PATH = os.path.join(ROOT_PATH, "python")
OCIO_PATH = os.path.join(ROOT_PATH, "ocio")


OCIO_CONFIG = os.path.join(OCIO_PATH, "studio-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio")
OCIO_SPACES = {
    "input": "sRGB Encoded Rec.709 (sRGB)",
    "working": "ACEScg",
    "display": "sRGB - Display",
}

CAMERA_DEVICE = "/dev/video0"

FORMAT = {
    "width": 1920,
    "height": 1080,
    "pixelformat": "MJPG",
    "fps": 30,
}

CONTROLS = {
    "auto_exposure": 1,
    "exposure_dynamic_framerate": 0,
    "exposure_time_absolute": 300,
    "gain": 156,

    "white_balance_automatic": 0,
    "white_balance_temperature": 4000,

    "focus_automatic_continuous": 0,
    "focus_absolute": 0,
}
