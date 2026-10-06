#!/bin/zsh
# Build Caffeine for Citrix into a distributable .app and .dmg.
#
#   ./build.sh            ad-hoc signed (free, users right-click → Open)
#   ./build.sh --sign     signed + notarized with your Developer ID
#
# For --sign, set these first:
#   export DEVELOPER_ID="Developer ID Application: Your Name (TEAMID)"
#   export NOTARY_PROFILE="caffeine-notary"
# Create the notary profile once with:
#   xcrun notarytool store-credentials "caffeine-notary" \
#     --apple-id you@example.com --team-id TEAMID --password APP_SPECIFIC_PASSWORD

set -e
cd "$(dirname "$0")"

APP_NAME="Caffeine for Citrix"
SIGN_MODE="adhoc"
[[ "$1" == "--sign" ]] && SIGN_MODE="developer"

VERSION=$(grep -m1 '__version__ = ' caffeine_citrix.py | cut -d'"' -f2)
echo "==> Building ${APP_NAME} ${VERSION} (${SIGN_MODE})"

# 1. Isolated build environment
if [[ ! -d .venv ]]; then
  echo "==> Creating .venv"
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt py2app

# 2. Icon
if [[ ! -f assets/icon.icns ]]; then
  echo "==> assets/icon.icns missing; run make_icon.py first" >&2
  exit 1
fi

# 3. Bundle
echo "==> Running py2app"
rm -rf build dist
.venv/bin/python setup.py py2app >/dev/null

APP="dist/${APP_NAME}.app"
[[ -d "$APP" ]] || { echo "Build failed: $APP not found" >&2; exit 1; }

# 4. Sign. Ad-hoc signing is mandatory on Apple Silicon, not optional.
if [[ "$SIGN_MODE" == "developer" ]]; then
  : "${DEVELOPER_ID:?Set DEVELOPER_ID to your 'Developer ID Application: ...' identity}"
  : "${NOTARY_PROFILE:?Set NOTARY_PROFILE to your stored notarytool profile name}"
  echo "==> Signing with Developer ID"
  # Hardened runtime is required for notarization.
  codesign --force --deep --options runtime --timestamp \
           --sign "$DEVELOPER_ID" "$APP"
else
  echo "==> Ad-hoc signing"
  codesign --force --deep --sign - "$APP"
fi
codesign --verify --strict "$APP"

# 5. DMG
DMG="dist/CaffeineForCitrix-${VERSION}-$(uname -m).dmg"
echo "==> Building ${DMG}"
STAGE=$(mktemp -d)
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE"

# 6. Notarize
if [[ "$SIGN_MODE" == "developer" ]]; then
  echo "==> Submitting to Apple for notarization (this takes a few minutes)"
  xcrun notarytool submit "$DMG" --keychain-profile "$NOTARY_PROFILE" --wait
  echo "==> Stapling"
  xcrun stapler staple "$DMG"
  xcrun stapler validate "$DMG"
  spctl -a -vvv -t install "$DMG" || true
fi

echo ""
echo "✅ Done: $DMG"
du -sh "$DMG"
