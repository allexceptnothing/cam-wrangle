import PyOpenColorIO as OCIO

from config import OCIO_CONFIG

config = OCIO.Config.CreateFromFile(OCIO_CONFIG)

print("--- COLOR SPACES (For Input/Working) ---")
# This lists all available spaces
for cs in config.getColorSpaces():
    print(f"Space: {cs.getName()}")

print("\n--- DISPLAYS & VIEWS (For Output) ---")
# This is where the 'S-Curve' filmic looks usually live in v2
for display in config.getDisplays():
    for view in config.getViews(display):
        print(f"Display: {display} | View: {view}")
