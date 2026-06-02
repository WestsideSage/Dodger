"""WT-13: the production SPA fallback must not be walked out of frontend/dist.

The catch-all that serves the built SPA (``server.serve_frontend``) used to do
``FileResponse(frontend_dist / full_path)`` whenever that path resolved to an
existing file — so an encoded ``../`` (or a Windows ``..\\``) could escape the
bundle and return an arbitrary local repo file. The fix resolves the candidate
against the filesystem and serves it only when it stays inside the dist root,
falling back to ``index.html`` otherwise.

This module proves the containment two ways:

* a direct call to the route handler with raw traversal strings (the strings an
  attacker controls, before any ASGI/httpx normalization) never returns a file
  outside the dist root; and
* an end-to-end TestClient request for a sentinel file planted outside the dist
  never leaks that sentinel's contents.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient
from starlette.responses import FileResponse

from dodgeball_sim import server

_DIST = (Path(server.__file__).resolve().parent.parent.parent / "frontend" / "dist").resolve()
_INDEX = _DIST / "index.html"
_SENTINEL = _DIST.parent / "WT13_SENTINEL_secret.txt"
_SENTINEL_MARKER = "TOP-SECRET-LEAK-MARKER-WT13"


def setup_module(module):  # noqa: D401 - pytest hook
    """Plant a sentinel file one directory above frontend/dist."""
    _SENTINEL.write_text(_SENTINEL_MARKER, encoding="utf-8")


def teardown_module(module):  # noqa: D401 - pytest hook
    _SENTINEL.unlink(missing_ok=True)


def _call_handler(full_path: str):
    """Invoke the SPA fallback handler directly with a raw path string."""
    return asyncio.run(server.serve_frontend(full_path))


def _served_index(response) -> bool:
    """True when the response is the injected index.html fallback (not a file)."""
    body = getattr(response, "body", b"")
    text = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else str(body)
    return '<div id="root">' in text and _SENTINEL_MARKER not in text


def test_handler_rejects_raw_parent_traversal_to_sentinel():
    """Raw ``../`` strings (pre-normalization) must resolve to index, not the file."""
    response = _call_handler("../WT13_SENTINEL_secret.txt")
    assert not isinstance(response, FileResponse)
    assert _served_index(response)


def test_handler_rejects_deep_traversal_outside_dist():
    response = _call_handler("../../frontend/WT13_SENTINEL_secret.txt")
    assert not isinstance(response, FileResponse)
    assert _served_index(response)


def test_handler_rejects_absolute_path_escape():
    """An absolute path that escapes the dist root must fall back to index."""
    response = _call_handler(str(_SENTINEL))
    assert not isinstance(response, FileResponse)
    assert _served_index(response)


def test_handler_still_serves_a_real_in_tree_file():
    """A legitimate in-bundle file is still served (containment is not over-broad)."""
    response = _call_handler("favicon.svg")
    assert isinstance(response, FileResponse)
    assert Path(response.path).resolve() == (_DIST / "favicon.svg")


def test_end_to_end_encoded_traversal_never_leaks_sentinel():
    """No encoded traversal variant may return the out-of-tree sentinel content."""
    server.enable_launch_token_guard(False)
    client = TestClient(server.app)
    variants = [
        "/../WT13_SENTINEL_secret.txt",
        "/..%2FWT13_SENTINEL_secret.txt",
        "/%2e%2e%2fWT13_SENTINEL_secret.txt",
        "/....//WT13_SENTINEL_secret.txt",
        "/..%5CWT13_SENTINEL_secret.txt",
        "/assets/../../WT13_SENTINEL_secret.txt",
    ]
    for raw in variants:
        response = client.get(raw)
        assert _SENTINEL_MARKER not in response.text, f"traversal leaked via {raw!r}"
