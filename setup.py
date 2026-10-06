"""py2app build script for Caffeine for Citrix.

Build a standalone .app bundle:

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt py2app
    .venv/bin/python setup.py py2app

The result is dist/Caffeine for Citrix.app
"""

import re
import pathlib

from setuptools import setup

APP_NAME = "Caffeine for Citrix"
BUNDLE_ID = "com.saulporras.caffeine-citrix"

# Single source of truth: read the version out of the app itself rather
# than duplicating it here where the two could drift apart.
_source = pathlib.Path("caffeine_citrix.py").read_text(encoding="utf-8")
_match = re.search(r'^__version__ = "([^"]+)"', _source, re.MULTILINE)
if _match is None:
    raise SystemExit("Could not find __version__ in caffeine_citrix.py")
VERSION = _match.group(1)

OPTIONS = {
    "argv_emulation": False,  # Interferes with menu bar apps; must stay off.
    "iconfile": "assets/icon.icns",
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
        "NSHumanReadableCopyright": "MIT License",
        # Menu bar only: no Dock icon, no app switcher entry.
        "LSUIElement": True,
        "LSMinimumSystemVersion": "12.0",
        # Shown in the macOS permission prompt.
        "NSAppleEventsUsageDescription": (
            "Caffeine for Citrix sends a keystroke to Citrix Viewer to keep "
            "your remote session from timing out."
        ),
    },
    # PyObjC pulls these in dynamically, so py2app cannot detect them.
    "packages": ["rumps"],
    "includes": ["Quartz", "ApplicationServices"],
}

setup(
    name=APP_NAME,
    version=VERSION,
    app=["caffeine_citrix.py"],
    data_files=[],
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
