#!/usr/bin/env python3
"""Caffeine for Citrix Workspace — macOS menu bar app.

Keeps Citrix remote sessions from locking by posting a harmless keystroke
directly to each Citrix Viewer process via CGEventPostToPid, which reaches
the session regardless of which Space or display it is on.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import subprocess
import sys

import rumps
import Quartz
from ApplicationServices import (
    AXIsProcessTrustedWithOptions,
    kAXTrustedCheckOptionPrompt,
)

__version__ = "1.0.0"

CITRIX_PROCESS = "Citrix Viewer"
LOG_PATH = os.path.expanduser("~/Library/Logs/caffeine_citrix.log")

#: Virtual keycode for Left Control. A bare modifier press is the safest
#: possible keystroke: it triggers no shortcut on macOS or Windows and
#: types nothing into the remote session.
KEYCODE_LEFT_CONTROL = 59

DEFAULT_INTERVAL = 120
INTERVALS = {
    "Every 60 seconds": 60,
    "Every 2 minutes": 120,
    "Every 5 minutes": 300,
}

#: pgrep is given a hard timeout so a wedged process can never stall the
#: menu bar run loop, which would freeze the UI.
PGREP_TIMEOUT = 5


def _configure_logging() -> logging.Logger:
    """Set up a size-capped rotating log.

    This app is designed to run for weeks at a time, so an uncapped log file
    would grow without bound. INFO keeps the file useful without logging a
    line every tick.
    """
    logger = logging.getLogger("caffeine_citrix")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        # encoding is explicit: inside an .app bundle the default encoding
        # is ASCII, which raises UnicodeEncodeError on any non-ASCII log text.
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_PATH, maxBytes=1_000_000, backupCount=2, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # A read-only or missing Logs directory must not prevent the app
        # from starting; console logging alone is enough.
        pass

    # In a bundled .app stdout may be an ASCII pipe or absent entirely, so
    # console logging is best-effort and must never break startup.
    try:
        # A bundled .app gets an ASCII stdout; force UTF-8 so log text
        # containing em dashes or check marks does not raise on write.
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    except (OSError, ValueError, AttributeError):
        pass

    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


log = _configure_logging()


def accessibility_trusted(prompt: bool = False) -> bool:
    """Report whether this process may post events to other applications.

    Without Accessibility permission CGEventPostToPid fails silently, so
    this check is the only way to tell the user why nothing is happening.
    Passing ``prompt=True`` asks macOS to show the system grant dialog.
    """
    options = {kAXTrustedCheckOptionPrompt: bool(prompt)}
    return bool(AXIsProcessTrustedWithOptions(options))


def get_citrix_pids() -> list[int]:
    """Return the PIDs of every running Citrix Viewer process."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", CITRIX_PROCESS],
            capture_output=True,
            text=True,
            timeout=PGREP_TIMEOUT,
        )
    except (subprocess.SubprocessError, OSError):
        log.exception("pgrep failed; assuming no Citrix sessions this tick")
        return []

    # pgrep exits 1 when nothing matches, which is a normal idle state.
    if result.returncode != 0:
        return []

    pids = []
    for token in result.stdout.split():
        try:
            pids.append(int(token))
        except ValueError:
            log.warning("Ignoring unparseable pgrep output: %r", token)
    return pids


def send_keepalive() -> int:
    """Post a Control keypress to every Citrix Viewer process.

    Returns the number of processes the keystroke was posted to. Zero means
    no session is open, which is an ordinary idle state rather than an error.

    CGEventPostToPid returns no status, so a successful return proves only
    that the event was posted, not that Citrix consumed it. Accessibility
    permission is verified separately by the caller.
    """
    pids = get_citrix_pids()
    if not pids:
        return 0

    delivered = 0
    for pid in pids:
        posted = False
        for is_down in (True, False):
            event = Quartz.CGEventCreateKeyboardEvent(None, KEYCODE_LEFT_CONTROL, is_down)
            if event is None:
                log.error("Failed to create keyboard event for PID %d", pid)
                break
            Quartz.CGEventPostToPid(pid, event)
            posted = True
        if posted:
            delivered += 1

    log.info("Keepalive posted to %d session(s): %s", delivered, pids)
    return delivered


class CaffeineCitrixApp(rumps.App):
    """Menu bar controller.

    The timer runs continuously once started. A missing Citrix session is
    treated as a quiet tick rather than a reason to stop, so sessions opened
    later are picked up automatically.
    """

    IDLE_TITLE = "☕"
    ACTIVE_TITLE = "☕🟢"
    WARNING_TITLE = "☕⚠️"

    def __init__(self) -> None:
        super().__init__("☕", quit_button=None)

        self.active = False
        self.interval = DEFAULT_INTERVAL
        self._warned_about_accessibility = False

        self.toggle_item = rumps.MenuItem("Start", callback=self.toggle)
        self.status_item = rumps.MenuItem("Status: Stopped")
        self.status_item.set_callback(None)  # Render as a non-clickable label.

        interval_menu = rumps.MenuItem("Interval")
        self.interval_items: dict[str, int] = {}
        for label, seconds in INTERVALS.items():
            item = rumps.MenuItem(label, callback=self.set_interval)
            item.state = 1 if seconds == self.interval else 0
            interval_menu.add(item)
            self.interval_items[label] = seconds

        self.menu = [
            self.toggle_item,
            self.status_item,
            None,
            interval_menu,
            None,
            rumps.MenuItem(f"Version {__version__}", callback=None),
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]

        self.timer = rumps.Timer(self.tick, self.interval)

    # -- state -----------------------------------------------------------

    def _set_status(self, text: str) -> None:
        self.status_item.title = f"Status: {text}"

    def toggle(self, _) -> None:
        if self.active:
            self.stop()
        else:
            self.start()

    def start(self) -> None:
        log.info("Starting keepalive (interval=%ds)", self.interval)
        self.active = True
        self.title = self.ACTIVE_TITLE
        self.toggle_item.title = "Stop"
        self._set_status("Running")

        # rumps.Timer only honours an interval change while stopped, so the
        # timer is always configured before it is started.
        self.timer.stop()
        self.timer.interval = self.interval
        self.timer.start()

        self.tick(None)  # Give immediate feedback instead of waiting a full period.

    def stop(self) -> None:
        log.info("Stopping keepalive")
        self.active = False
        self.title = self.IDLE_TITLE
        self.toggle_item.title = "Start"
        self._set_status("Stopped")
        if self.timer.is_alive():
            self.timer.stop()

    # -- timer -----------------------------------------------------------

    def tick(self, _) -> None:
        # Permission can be revoked at any time in System Settings, so it is
        # rechecked every tick rather than only at launch.
        if not accessibility_trusted():
            self.title = self.WARNING_TITLE
            self._set_status("Needs Accessibility permission")
            if not self._warned_about_accessibility:
                self._warned_about_accessibility = True
                log.error("Accessibility permission missing — keystrokes cannot be delivered")
                rumps.notification(
                    title="Caffeine for Citrix",
                    subtitle="Accessibility permission required",
                    message="Enable it in System Settings → Privacy & Security → Accessibility, then relaunch.",
                )
            return

        self._warned_about_accessibility = False

        try:
            count = send_keepalive()
        except Exception:
            # A failure here must never kill the timer; the next tick retries.
            log.exception("Keepalive failed — retrying next tick")
            self.title = self.WARNING_TITLE
            self._set_status("Running (send failed)")
            return

        self.title = self.ACTIVE_TITLE
        if count == 0:
            self._set_status("Running (waiting for Citrix)")
        elif count == 1:
            self._set_status("Running ✓ (1 session)")
        else:
            self._set_status(f"Running ✓ ({count} sessions)")

    def set_interval(self, sender) -> None:
        for item in self.menu["Interval"].values():
            item.state = 0
        sender.state = 1
        self.interval = self.interval_items[sender.title]
        log.info("Interval changed to %ds", self.interval)

        if self.active:
            self.timer.stop()
            self.timer.interval = self.interval
            self.timer.start()

    def quit_app(self, _) -> None:
        self.stop()
        rumps.quit_application()


def main() -> None:
    log.info("Caffeine for Citrix %s starting — log: %s", __version__, LOG_PATH)
    # Prompt once at launch so first-run users are sent straight to the
    # right System Settings pane instead of discovering a silent failure.
    if not accessibility_trusted(prompt=True):
        log.warning("Accessibility permission not yet granted")
    CaffeineCitrixApp().run()


if __name__ == "__main__":
    main()
