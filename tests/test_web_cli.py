from __future__ import annotations

import json
import os

from dodgeball_sim import web_cli


def test_choose_launch_ports_skips_unmanaged_occupied_defaults(monkeypatch):
    occupied = {8000, 5173}
    monkeypatch.setattr(web_cli, "_port_in_use", lambda port: port in occupied)

    ports = web_cli._choose_launch_ports(dev_mode=True)

    assert ports.backend == 8001
    assert ports.frontend == 5174


def test_stop_previous_launch_terminates_only_owned_processes(tmp_path, monkeypatch):
    state_path = tmp_path / ".dodgeball-web.json"
    state_path.write_text(
        json.dumps(
            {
                "root": str(tmp_path),
                "backend_pid": os.getpid(),
                "vite_pid": 12345,
                "backend_port": 8000,
                "frontend_port": 5173,
            }
        ),
        encoding="utf-8",
    )
    terminated: list[int] = []
    monkeypatch.setattr(web_cli, "_launch_state_path", lambda root: state_path)
    monkeypatch.setattr(web_cli, "_terminate_pid", lambda pid: terminated.append(pid) or True)

    stopped = web_cli._stop_previous_launch(tmp_path)

    assert stopped == [12345]
    assert terminated == [12345]
    assert not state_path.exists()


def test_stop_previous_launch_preserves_foreign_project_state(tmp_path, monkeypatch):
    state_path = tmp_path / ".dodgeball-web.json"
    state_path.write_text(
        json.dumps(
            {
                "root": str(tmp_path / "other"),
                "backend_pid": 111,
                "vite_pid": 222,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(web_cli, "_launch_state_path", lambda root: state_path)
    monkeypatch.setattr(web_cli, "_terminate_pid", lambda pid: (_ for _ in ()).throw(AssertionError(pid)))

    stopped = web_cli._stop_previous_launch(tmp_path)

    assert stopped == []
    assert state_path.exists()
