import numpy as np
import cv2
import PyOpenColorIO as OCIO



class OcioPipeline:
    def __init__(self, config_path, input_space, working_space, display_space, lut_path=None):
        self.config = OCIO.Config.CreateFromFile(config_path)
        self.params = (input_space, working_space, display_space, lut_path)
        self.last_state = None
        self.cpu_proc = None

    def update_processor(self, r, g, b, gain, force=False):
        # Only rebuild if values actually changed
        current_state = (r, g, b, gain)
        if current_state == self.last_state and not force:
            return

        in_sp, work_sp, disp_sp, lut_path = self.params
        group = OCIO.GroupTransform()

        # 1. IDT
        group.appendTransform(OCIO.ColorSpaceTransform(src=in_sp, dst=work_sp))

        # 2. White Balance / Gain Matrix
        m44 = [r * gain, 0, 0, 0, 0, g * gain, 0, 0, 0, 0, b * gain, 0, 0, 0, 0, 1]
        group.appendTransform(OCIO.MatrixTransform(m44))

        # 3. Optional LUT (with Log conversion if needed)
        if lut_path:
            # Move to Log space for the LUT if it's a creative film LUT
            group.appendTransform(OCIO.ColorSpaceTransform(src=work_sp, dst="ACEScct"))
            group.appendTransform(OCIO.FileTransform(src=lut_path, interpolation=OCIO.INTERP_TETRAHEDRAL))
            group.appendTransform(OCIO.ColorSpaceTransform(src="ACEScct", dst=work_sp))

        # 4. ODT
        group.appendTransform(OCIO.ColorSpaceTransform(src=work_sp, dst=disp_sp))

        self.cpu_proc = self.config.getProcessor(group).getDefaultCPUProcessor()
        self.last_state = current_state

    def apply_inplace(self, rgb_flat):
        self.cpu_proc.applyRGB(rgb_flat)


class ColourPipeline:
    def __init__(self, width: int, height: int, ocio_pipe):
        self.ocio = ocio_pipe
        # Pre-allocate everything once
        self.f32_buffer = np.empty((height, width, 3), dtype=np.float32)
        self.u8_buffer = np.empty((height, width, 3), dtype=np.uint8)

    def process_bgr_u8(self, frame_bgr_u8, temp, tint, gain):
        # 1. BGR u8 -> RGB f32 (The correct way)
        # We use .astype but keep it efficient by using the pre-allocated buffer
        # Note: cv2.cvtColor can handle the u8->f32 shift if we scale after
        self.f32_buffer = frame_bgr_u8.astype(np.float32)
        cv2.multiply(self.f32_buffer, 1.0/255.0, dst=self.f32_buffer)
        cv2.cvtColor(self.f32_buffer, cv2.COLOR_BGR2RGB, dst=self.f32_buffer)


        # 2. Update OCIO (Lazy update)
        r, g, b = wb_multipliers_from_temp_tint(temp, tint)
        self.ocio.update_processor(r, g, b, gain * 4.5)

        # 3. Apply OCIO
        # Ensure we are passing the pointer to the same memory
        self.ocio.apply_inplace(self.f32_buffer.reshape(-1, 3))

        # 4. RGB f32 -> BGR u8
        # We MUST clamp before converting to u8 to prevent wrap-around (artifacting)
        np.clip(self.f32_buffer, 0, 1, out=self.f32_buffer)
        cv2.cvtColor(self.f32_buffer, cv2.COLOR_RGB2BGR, dst=self.f32_buffer)

        # Final scale to 255 and cast
        return (self.f32_buffer * 255.0).astype(np.uint8)

def wb_multipliers_from_temp_tint(temp: float, tint: float, slider_strength=0.5) -> np.ndarray:
    r = 1.0 + temp * slider_strength
    b = 1.0 - temp * slider_strength
    g = 1.0 + tint * slider_strength

    # Optional: keep overall luminance-ish stable by normalizing average
    # maybe replace with luma coeffficients
    avg = (r + g + b) / 3.0
    r, g, b = r / avg, g / avg, b / avg
    return np.array([r, g, b], dtype=np.float32)
