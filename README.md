<div align="center">

# ☕ Caffeine for Citrix

**Stop your Citrix session from locking while you work on another screen.**

A tiny macOS menu bar app that keeps remote Citrix sessions awake — across Spaces, across displays, without stealing focus.

[![Build](https://github.com/saulporras/caffeine-citrix-mac/actions/workflows/release.yml/badge.svg)](https://github.com/saulporras/caffeine-citrix-mac/actions/workflows/release.yml)
[![Platform](https://img.shields.io/badge/platform-macOS%2012%2B-black)](#requirements)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](#requirements)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ko-fi](https://img.shields.io/badge/buy%20me%20some-tokens-ff5e5b?logo=ko-fi&logoColor=white)](https://ko-fi.com/C5Q128BM5J)

</div>

---

## The problem

You're on a call, reading docs on your second monitor, or working in another Space. Meanwhile your Citrix session decides you're idle and locks. You come back, re-authenticate, and lose your place — again.

Keeping the *Mac* awake doesn't help. The timeout lives on the remote side, and it only cares about input reaching the session.

## The solution

Caffeine for Citrix sends one harmless keystroke to Citrix Viewer every couple of minutes. Enough to register as activity. Not enough to do anything else.

```
☕🟢  Status: Running ✓ (2 sessions)
```

## How it works

It posts a **bare Left Control key press** directly to each Citrix Viewer process using macOS's `CGEventPostToPid` API.

Two properties make this safe and reliable:

- **It's addressed to the process, not the screen.** The event reaches Citrix no matter which Space or display it's on — and never steals focus from whatever you're actually doing. Nothing flickers, nothing comes to the front.
- **A bare modifier key does nothing.** Control on its own triggers no shortcut on macOS or Windows, and types nothing into the remote session. No stray characters in your documents, no accidental hotkeys.

## Features

| | |
|---|---|
| 🖥️ **Multi-session** | Every open Citrix session gets the keepalive, not just the first |
| ♾️ **Always running** | Citrix closed? It waits. Reopen it and keepalives resume automatically — no restart, no babysitting |
| 🎯 **No focus stealing** | Events are posted to the process; your current window is never interrupted |
| ⏱️ **Adjustable interval** | 60s, 2min, or 5min from the menu |
| 🔒 **Honest status** | Tells you when Accessibility permission is missing instead of silently doing nothing |
| 🪶 **Tiny** | One Python file, two dependencies, no background daemon |

## Requirements

- macOS 12 (Monterey) or later
- Python 3.10 or later
- Citrix Workspace for Mac

```zsh
python3 --version    # need 3.10+
```

No Python 3.10+? Install it with [Homebrew](https://brew.sh): `brew install python`

## Install

### Option A — Download the app (recommended)

**1.** Grab the latest `.dmg` from [**Releases**](https://github.com/saulporras/caffeine-citrix-mac/releases).

**2.** Open it and drag **Caffeine for Citrix** to Applications.

**3.** Launch it. Because the app isn't notarized, macOS blocks the first launch — **right-click the app → Open**, then confirm. You only do this once.

**4.** Grant Accessibility permission (see below).

> [!NOTE]
> The release build is **Apple Silicon (arm64) only**. On an Intel Mac, use Option B.

### Option B — Run from source

```zsh
git clone https://github.com/saulporras/caffeine-citrix-mac.git
cd caffeine-citrix-mac
pip3 install -r requirements.txt --break-system-packages
python3 caffeine_citrix.py
```

A ☕ icon appears in your menu bar.

### Grant Accessibility permission

On first launch macOS will ask. Go to:

> **System Settings → Privacy & Security → Accessibility**

Enable **Caffeine for Citrix** (or, if running from source, the terminal you launched it from — Terminal, iTerm, or similar).

> [!IMPORTANT]
> **Quit and relaunch after granting permission.** macOS only applies Accessibility changes to a process when it restarts. Until you do, the menu bar shows ☕⚠️ and keystrokes won't be delivered.

## Usage

Click the ☕ icon:

- **Start** — begin sending keepalives. Citrix doesn't need to be open yet.
- **Interval** — how often to fire. Default is 2 minutes; use 60 seconds if your session locks in under 5.
- **Stop / Quit** — when you're done.

### Reading the menu bar

| Icon | Meaning |
|------|---------|
| ☕ | Stopped |
| ☕🟢 | Running |
| ☕⚠️ | Needs Accessibility permission, or a send failed |

### Status messages

| Status | Meaning |
|--------|---------|
| `Running ✓ (2 sessions)` | Working — keepalives going to both sessions |
| `Running (waiting for Citrix)` | No session open yet. It'll pick one up automatically |
| `Needs Accessibility permission` | Grant it in System Settings, then relaunch |

## Run at login

**System Settings → General → Login Items → +**

Add a small wrapper script so it launches without a visible Terminal window:

```zsh
#!/bin/zsh
exec /usr/bin/python3 /full/path/to/caffeine_citrix.py
```

Save it, `chmod +x` it, and add that file to Login Items.

## Troubleshooting

<details>
<summary><strong>The menu bar shows ☕⚠️</strong></summary>

Accessibility permission is missing or wasn't applied yet. Grant it in **System Settings → Privacy & Security → Accessibility**, then **quit and relaunch** the app — macOS won't apply the change to a running process.

If it's already enabled, toggle it off and on. macOS sometimes holds a stale permission entry after an app is moved or updated.
</details>

<details>
<summary><strong>It says "Running ✓" but my session still locked</strong></summary>

Your session's idle timeout may be shorter than your interval. Switch to **Every 60 seconds**.

If that doesn't help, the remote policy may track more than keyboard input — some configurations require mouse movement or count only in-session application activity. Check `~/Library/Logs/caffeine_citrix.log` to confirm keepalives are being posted.
</details>

<details>
<summary><strong>"Running (waiting for Citrix)" while Citrix is clearly open</strong></summary>

The app looks for a process named exactly `Citrix Viewer`. Confirm yours matches:

```zsh
pgrep -xl "Citrix Viewer"
```

Nothing returned? Find the real name and update `CITRIX_PROCESS` in the script:

```zsh
ps -axco command | sort -u | grep -i citrix
```
</details>

<details>
<summary><strong>ModuleNotFoundError on launch</strong></summary>

Dependencies went to a different Python than the one running the script:

```zsh
python3 -m pip install -r requirements.txt --break-system-packages
```

Using `python3 -m pip` guarantees they land in the interpreter you're actually using.
</details>

## Logs

```zsh
tail -f ~/Library/Logs/caffeine_citrix.log
```

Capped at 1 MB with two rotations, so it's safe to leave running indefinitely.

## FAQ

**Does this type anything into my session?**
No. It sends Control by itself, which produces no character and triggers no shortcut.

**Will it interrupt what I'm doing?**
No. The keystroke is posted directly to the Citrix process, so your active window never loses focus.

**Is this on the Mac App Store?**
No, and it can't be. App Store apps must be sandboxed, and the sandbox forbids sending input to other processes.

**Does it work with multiple monitors / Spaces?**
Yes — that's the main reason it posts to the process rather than simulating a global keystroke.

**Why not just keep my Mac awake?**
That solves a different problem. Your Mac staying awake doesn't stop the *remote* session from timing out.

## Building the app yourself

```zsh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt py2app
.venv/bin/python make_icon.py     # once, to create assets/icon.icns
./build.sh
```

Produces `dist/CaffeineForCitrix-<version>-<arch>.dmg`.

To sign and notarize with your own Apple Developer ID:

```zsh
xcrun notarytool store-credentials "caffeine-notary" \
  --apple-id you@example.com --team-id TEAMID --password APP_SPECIFIC_PASSWORD

export DEVELOPER_ID="Developer ID Application: Your Name (TEAMID)"
export NOTARY_PROFILE="caffeine-notary"
./build.sh --sign
```

A notarized build installs with no Gatekeeper warning and no right-click step.

## Releasing

Releases are built automatically by GitHub Actions on any `v*` tag:

```zsh
# 1. Bump __version__ in caffeine_citrix.py, then:
git tag v1.0.1
git push origin v1.0.1
```

The workflow builds the bundle, ad-hoc signs it, smoke-tests that it launches,
packages a DMG, and attaches it to a new GitHub Release. The tag must match
`__version__` or the build fails deliberately.

## Buy me some tokens

This is free and always will be. If it saved you from re-authenticating one
too many times, you can [**buy me some tokens**](https://ko-fi.com/C5Q128BM5J) ☕

<a href="https://ko-fi.com/C5Q128BM5J">
  <img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Buy me some tokens on Ko-fi" height="36">
</a>

## Credits

Inspired by [CaffeineForCitrixWorkspace](https://github.com/andyjmorgan/CaffeineForCitrixWorkspace) by Andy Morgan, which does the same job on Windows.

Built with [rumps](https://github.com/jaredks/rumps) and [PyObjC](https://pyobjc.readthedocs.io/).

## License

MIT — see [LICENSE](LICENSE).
