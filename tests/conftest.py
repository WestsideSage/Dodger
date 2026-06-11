"""Shared pytest fixtures for the Dodgeball Manager test suite.

WT-12 cascade fence
-------------------
The live server enforces a per-process launch token on every mutating ``/api``
request (CSRF defense for the local server). The in-process ``TestClient`` suite
has many tests that POST to those routes *without* a token (policy/tactics,
save-boundary, editor-lineup, auto-pilot, readiness, recruiting, offseason, …).

Enforcement is ON by the module default in ``server`` so production is protected
on import (no launcher wiring needed). This autouse fixture is the single place
the suite disables it: it pins the flag OFF per test and restores the prior
value afterwards. That keeps the whole suite green with zero per-file churn while
letting the dedicated WT-12 test flip enforcement ON inside its own body to
exercise both the rejected (missing/forged token -> 403) and allowed (valid
token) paths without leaking that state to any other test. ``conftest.py`` is a
pytest-only mechanism and is never imported by the running app.
"""

from __future__ import annotations

import pytest

from dodgeball_sim import server


@pytest.fixture(autouse=True)
def _disable_launch_token_guard():
    """Disable launch-token enforcement for the in-process TestClient suite."""
    previous = server._enforce_launch_token
    server._enforce_launch_token = False
    try:
        yield
    finally:
        server._enforce_launch_token = previous


@pytest.fixture(autouse=True)
def _isolate_server_shared_state():
    """Fence the server module's per-process shared state between tests.

    V20 §7.5 flake root cause class: ``server.app.dependency_overrides`` and
    ``server._active_save_path`` are process-global. Most tests that set them
    restore them, but any test that fails *between* set and restore (or any
    future test that forgets) poisons every later test in the session — the
    reported ``test_server_save_boundary`` failure appeared exactly once in a
    full run and never in isolation, the signature of such a leak. This net
    makes the whole class impossible instead of chasing one instance:
    within-test behavior is untouched; after every test the overrides map is
    emptied and the active-save pointer is restored to its pre-test value.
    """
    previous_save_path = server._active_save_path
    try:
        yield
    finally:
        server.app.dependency_overrides.clear()
        server._active_save_path = previous_save_path
