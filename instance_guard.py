"""Keep a second Dissman from running alongside the systemd service.

The Pi launches dissman.py twice: the systemd unit (via start.sh, which pulls
code, publishes logs and recovers submissions) and a legacy desktop autostart
entry (~/.config/autostart/dissman.desktop). Two copies fight over the USB
printer ("Resource busy"), delete each other's images, and double-charge the
image API. The autostart entry stays as a fallback; a copy it starts just
exits while the service is up. Stdlib only, never raises.
"""

from __future__ import annotations

import subprocess

SERVICE = "dissman.service"
# States in which the service's copy is running or about to (ExecStartPre
# sleeps 10s, during which the unit reports "activating").
_UP_STATES = {"active", "activating", "reloading"}


def service_state(service: str = SERVICE) -> str | None:
    """`systemctl is-active` output, or None where systemctl isn't usable."""
    try:
        out = subprocess.run(["systemctl", "is-active", service],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def should_defer_to_service(env, get_state=service_state) -> bool:
    """True if this copy should exit because the systemd service owns the kiosk."""
    if env.get("INVOCATION_ID"):          # systemd sets this for its own services
        return False
    if env.get("DISSMAN_ALLOW_DUPLICATE") == "1":
        return False
    return get_state() in _UP_STATES
