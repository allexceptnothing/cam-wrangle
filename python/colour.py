import numpy as np
import cv2
import PyOpenColorIO as OCIO



class OcioPipeline:
    def __init__(self, config_path: str, input_space: str, working_space: str, display_space: str):
        self.config = OCIO.Config.CreateFromFile(config_path)
        self.in_cpu  = self.config.getProcessor(input_space, working_space).getDefaultCPUProcessor()
        self.out_cpu = self.config.getProcessor(working_space, display_space).getDefaultCPUProcessor()

    def apply_in_to_work_inplace(self, rgb_flat_n3: np.ndarray) -> None:
        self.in_cpu.applyRGB(rgb_flat_n3)

    def apply_work_to_disp_inplace(self, rgb_flat_n3: np.ndarray) -> None:
        self.out_cpu.applyRGB(rgb_flat_n3)

    def get_colourspace_names(self):
        return list(self.config.getColorSpaceNames())


class ColourPipeline:
    def __init__(self, width: int, height: int, ocio_pipe):
        self.w = width
        self.h = height
        self.ocio = ocio_pipe

        # Single working/display buffer (RGB float32)
        self.rgb = np.empty((height, width, 3), dtype=np.float32)
        self.rgb_flat = self.rgb.reshape(-1, 3)

        # Output buffer (BGR uint8)
        self.bgr_out = np.empty((height, width, 3), dtype=np.uint8)

    def process_bgr_u8(self, frame_bgr_u8: np.ndarray, temp: float, tint: float, gain: float) -> np.ndarray:
        # 1) copy BGR u8 -> BGR float32 in-place
        np.multiply(frame_bgr_u8, (1.0 / 255.0), out=self.rgb, casting="unsafe")  # writes into rgb as float32

        # 2) swap BGR->RGB in-place (swap channels 0 and 2)
        self.rgb[..., [0, 2]] = self.rgb[..., [2, 0]]

        # OCIO input->working (in-place)
        self.ocio.apply_in_to_work_inplace(self.rgb_flat)

        # Grade in-place (RGB)
        wb = wb_multipliers_from_temp_tint(temp, tint)
        self.rgb *= wb
        self.rgb *= (gain * 4.5)

        # OCIO working->display (in-place)  (reuses same buffer)
        self.ocio.apply_work_to_disp_inplace(self.rgb_flat)

        # Clamp + pack to BGR u8 (no alloc)
        np.clip(self.rgb, 0.0, 1.0, out=self.rgb)
        self.bgr_out[...] = (self.rgb[..., ::-1] * 255.0 + 0.5).astype(np.uint8)

        return self.bgr_out


def wb_multipliers_from_temp_tint(temp: float, tint: float, slider_strength=0.5) -> np.ndarray:
    r = 1.0 + temp * slider_strength
    b = 1.0 - temp * slider_strength
    g = 1.0 + tint * slider_strength

    # Optional: keep overall luminance-ish stable by normalizing average
    # maybe replace with luma coeffficients
    avg = (r + g + b) / 3.0
    r, g, b = r / avg, g / avg, b / avg
    return np.array([r, g, b], dtype=np.float32)
