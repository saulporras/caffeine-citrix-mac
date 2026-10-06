#!/usr/bin/env python3
"""Generate assets/icon.icns from the ☕ emoji.

Run once before the first build:  .venv/bin/python make_icon.py
"""

import os
import shutil
import subprocess

from AppKit import (
    NSAttributedString,
    NSBitmapImageRep,
    NSCalibratedRGBColorSpace,
    NSFont,
    NSFontAttributeName,
    NSGraphicsContext,
    NSMakePoint,
    NSPNGFileType,
)

ICONSET = "assets/icon.iconset"
# iconutil requires exactly these sizes, each also at @2x.
SIZES = (16, 32, 128, 256, 512)


def render(size: int, path: str) -> None:
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, size, size, 8, 4, True, False, NSCalibratedRGBColorSpace, 0, 0
    )
    context = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(context)

    font = NSFont.fontWithName_size_("Apple Color Emoji", size * 0.72) or NSFont.systemFontOfSize_(size * 0.72)
    text = NSAttributedString.alloc().initWithString_attributes_("☕", {NSFontAttributeName: font})
    bounds = text.size()
    text.drawAtPoint_(NSMakePoint((size - bounds.width) / 2.0, (size - bounds.height) / 2.0))

    NSGraphicsContext.restoreGraphicsState()
    rep.representationUsingType_properties_(NSPNGFileType, {}).writeToFile_atomically_(path, True)


def main() -> None:
    shutil.rmtree(ICONSET, ignore_errors=True)
    os.makedirs(ICONSET, exist_ok=True)

    for size in SIZES:
        render(size, f"{ICONSET}/icon_{size}x{size}.png")
        render(size * 2, f"{ICONSET}/icon_{size}x{size}@2x.png")

    subprocess.run(["iconutil", "-c", "icns", ICONSET, "-o", "assets/icon.icns"], check=True)
    print("Wrote assets/icon.icns")


if __name__ == "__main__":
    main()
