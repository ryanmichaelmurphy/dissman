import subprocess
from unittest.mock import patch

import pytest

from instance_guard import service_state, should_defer_to_service


def test_systemd_launched_copy_always_runs():
    env = {"INVOCATION_ID": "abc123"}
    assert should_defer_to_service(env, lambda: "active") is False


@pytest.mark.parametrize("state", ["active", "activating", "reloading"])
def test_desktop_copy_defers_when_service_is_up(state):
    assert should_defer_to_service({}, lambda: state) is True


@pytest.mark.parametrize("state", ["inactive", "failed", "unknown", None])
def test_desktop_copy_runs_when_service_is_down(state):
    # Fallback: if the service is disabled or broken, the desktop entry
    # still brings the kiosk up.
    assert should_defer_to_service({}, lambda: state) is False


def test_override_env_lets_a_manual_copy_run():
    env = {"DISSMAN_ALLOW_DUPLICATE": "1"}
    assert should_defer_to_service(env, lambda: "active") is False


def test_service_state_reads_systemctl_output():
    done = subprocess.CompletedProcess(args=[], returncode=3, stdout="activating\n")
    with patch("instance_guard.subprocess.run", return_value=done) as m:
        assert service_state() == "activating"
    assert m.call_args.args[0][:2] == ["systemctl", "is-active"]


@pytest.mark.parametrize("exc", [FileNotFoundError(), subprocess.TimeoutExpired("systemctl", 5)])
def test_service_state_is_none_without_systemctl(exc):
    # Windows/macOS dev boxes have no systemctl; never block startup.
    with patch("instance_guard.subprocess.run", side_effect=exc):
        assert service_state() is None
