import numpy as np
import PyOpenColorIO as OCIO
import cv2

class OcioPipeline:
    def __init__(self, config_path, input_space, working_space, display_device, view_name):
        self.config = OCIO.Config.CreateFromFile(config_path)
        self.params = {
            "input": input_space,
            "working": working_space,
            "device": display_device,
            "view": view_name
        }
        self.lut_map = None
        self.res = 32 # 32x32x32 is plenty for real-time


    def update_processor(self, r, g, b, gain, slope_val=1.0, power_val=1.0, offset=0.0):
        group = OCIO.GroupTransform()
        group.appendTransform(OCIO.ColorSpaceTransform(src=self.params["input"], dst=self.params["working"]))

        cdl = OCIO.CDLTransform()
        cdl.setSlope([slope_val, slope_val, slope_val])
        cdl.setPower([power_val, power_val, power_val])
        cdl.setOffset([offset, offset, offset])
        group.appendTransform(cdl)

        m44 = [r * gain, 0, 0, 0, 0, g * gain, 0, 0, 0, 0, b * gain, 0, 0, 0, 0, 1]
        group.appendTransform(OCIO.MatrixTransform(m44))

        dt = OCIO.DisplayViewTransform()
        dt.setSrc(self.params["working"])
        dt.setDisplay(self.params["device"])
        dt.setView(self.params["view"])
        group.appendTransform(dt)

        cpu = self.config.getProcessor(group).getDefaultCPUProcessor()

        #bake to map
        grid = np.linspace(0, 1, self.res, dtype=np.float32)
        b_g, g_g, r_g = np.meshgrid(grid, grid, grid, indexing='ij')
        lut_input = np.stack([r_g, g_g, b_g], axis=-1).reshape(-1, 3)

        cpu.applyRGB(lut_input)
        self.lut_map = lut_input.reshape(self.res * self.res, self.res, 3)

    def apply_lut(self, frame_f32):
        res = self.res
        # Use a local view to avoid repeated attribute lookups
        r = frame_f32[:,:,0] * (res - 1)
        g = frame_f32[:,:,1] * (res - 1)
        b = frame_f32[:,:,2] * (res - 1)

        map_x = r.astype(np.float32)
        map_y = (g + np.floor(b) * res).astype(np.float32)

        # Use the 'dst' parameter to write directly back into the input buffer
        # This saves the allocation of a 24MB array
        cv2.remap(self.lut_map, map_x, map_y, cv2.INTER_LINEAR, dst=frame_f32)
        return frame_f32
