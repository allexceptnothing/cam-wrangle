from device import apply_camera_preset
from preview import run_preview
import config


if __name__ == "__main__":
    apply_camera_preset(config, dry_run=False)
    run_preview(config, timers=True)
