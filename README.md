# Cam Wrangle


## Concept
Take ownership of as many of the settings and as much of the colour pipeline for Logitech C930e webcam as possible, then pass the stream on as a device.
Built for Linux Mint 22.3


- set all parameters to static constants
- interpret the compromised 8bit "sRGB" with Aces IDT e.g. 'sRGB Encoded Rec.709 (sRGB)' > 'ACEScg'
    - apply any additional "faux-linearization" to take whatever flattened colour settings are available in the cam pre USB transfer to a guesstimated linear look
- apply parametric UI grades via native OCIO transforms
- apply optional LUT (with optional pre & post OCIO transforms e.g. ACEScg > acescct)
- apply ODT device transform e.g. 'ACEScg' > 'sRGB - Display'


## Dependencies
    OCIO:
    - ocio: 2.5
    - studio-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio

    Python:
    - python=3.12
    - moderngl
    - glfw
    - numpy=1.26.4
    - opencv
    - pip
    - pip:
        - glfw
        - opencolorio

    Linux:
    - libgl1
    - libegl1
    - libgl1-mesa-glx
    - libegl1-mesa
    - libgl1-mesa-dev
    - libegl1-mesa-dev


## Helpers
"v4l2-ctl --list-devices"
"v4l2-ctl -d /dev/video0 --list-formats-ext"
