import subprocess

def run(cmd):
    print(">>", " ".join(cmd))
    subprocess.run(cmd, check=True)


def apply_camera_preset(cfg, dry_run=False):
    print("Applying base config to camera:\n")
    device = cfg.CAMERA_DEVICE

    if not dry_run:
        run([
            "v4l2-ctl",
            "-d", device,
            f"--set-fmt-video=width={cfg.FORMAT['width']},"
            f"height={cfg.FORMAT['height']},"
            f"pixelformat={cfg.FORMAT['pixelformat']}",
        ])

        run([
            "v4l2-ctl",
            "-d", device,
            f"--set-parm={cfg.FORMAT['fps']}",
        ])

        #touch
        run(["v4l2-ctl","-d",device, "--stream-mmap=3", "--stream-count=1"])

        #check that the format set worked
        run(["v4l2-ctl", "-d", device, "--get-fmt-video"])
        run(["v4l2-ctl", "-d", device, "--get-parm"])

        for name, value in cfg.CONTROLS.items():
            run([
                "v4l2-ctl",
                "-d", device,
                f"--set-ctrl={name}={value}",
            ])


    verify = [
        "auto_exposure",
        "exposure_time_absolute",
        "gain",
        "white_balance_automatic",
        "white_balance_temperature",
        "focus_automatic_continuous",
        "focus_absolute",
    ]
    parameters = cfg.FORMAT | cfg.CONTROLS
    for ctrl in verify:
        run([
            "v4l2-ctl",
            "-d", device,
            f"--get-ctrl={ctrl}",
        ])
        print(f"Expected value: {parameters[ctrl]}")
