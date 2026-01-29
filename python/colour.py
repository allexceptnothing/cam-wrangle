import numpy as np
import cv2
from config import FORMAT

class ColourPipeline:
    def __init__(self, config, width: int, height: int, ocio_pipe):
        self.w, self.h = width, height
        self.ocio = ocio_pipe
        # We can handle more resolution now with the LUT remap
        # self.cw, self.ch = 640, 360
        self.cw, self.ch = config.COLOUR_DOWNSAMPLING['width'], config.COLOUR_DOWNSAMPLING['height']


    def process_bgr_u8(self, frame_bgr_u8, temp, tint, gain):
        # 1. Resize to working resolution
        small = cv2.resize(frame_bgr_u8, (self.cw, self.ch), interpolation=cv2.INTER_AREA)
        small = cv2.flip(small, 1)

        # small = cv2.resize(frame_bgr_u8, (self.cw, self.ch), interpolation=cv2.INTER_NEAREST)
        # 2. Convert to Float (0.0 - 1.0)
        rgb_f32 = cv2.cvtColor(small, cv2.COLOR_BGR2RGB).astype(np.float32) * (1.0/255.0)

        # 3. FAST LUT LOOKUP
        processed = self.ocio.apply_lut(rgb_f32)

        # 4. Back to BGR U8
        np.clip(processed * 255.0, 0, 255, out=processed)
        out_u8 = cv2.cvtColor(processed.astype(np.uint8), cv2.COLOR_RGB2BGR)

        return cv2.resize(out_u8, (self.w, self.h), interpolation=cv2.INTER_LINEAR)

def wb_multipliers_from_temp_tint(temp: float, tint: float, slider_strength=0.5) -> np.ndarray:
    r = 1.0 + temp * slider_strength
    b = 1.0 - temp * slider_strength
    g = 1.0 + tint * slider_strength
    avg = (r + g + b) / 3.0
    return np.array([r / avg, g / avg, b / avg], dtype=np.float32)
