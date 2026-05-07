from __future__ import annotations

from dataclasses import dataclass
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import uvicorn
import webbrowser
from pathlib import Path

DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 5173


@dataclass(frozen=True)
class LaunchPorts:
    backend: int
    frontend: int | None = None


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _project_root() -> Path:
    """Return the repo root (where frontend/ lives)."""
    candidate = Path(__file__).parent.parent.parent
    if (candidate / "frontend").exists():
        return candidate
    return Path.cwd()


def _open_browser(url: str, delay: float = 1.5) -> None:
    time.sleep(delay)
    webbrowser.open(url)


def _launch_state_path(root: Path) -> Path:
    return root / ".dodgeball-web.json"


def _normalize_path(path: str | Path) -> str:
    return str(Path(path).resolve()).casefold()


def _terminate_pid(pid: int) -> bool:
    if pid <= 0 or pid == os.getpid():
        return False
    if sys.platform == "win32":
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    try:
        os.killpg(pid, signal.SIGTERM)
        return True
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except OSError:
            return False


def _stop_previous_launch(root: Path) -> list[int]:
    state_path = _launch_state_path(root)
    if not state_path.exists():
        return []
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state_path.unlink(missing_ok=True)
        return []

    if _normalize_path(state.get("root", "")) != _normalize_path(root):
        return []

    stopped: list[int] = []
    for key in ("vite_pid", "backend_pid"):
        try:
            pid = int(state.get(key) or 0)
        except (TypeError, ValueError):
            continue
        if pid == os.getpid():
            continue
        if _terminate_pid(pid):
            stopped.append(pid)
    state_path.unlink(missing_ok=True)
    if stopped:
        time.sleep(0.5)
    return stopped


def _write_launch_state(
    root: Path,
    *,
    backend_port: int,
    frontend_port: int | None,
    backend_pid: int,
    vite_pid: int | None = None,
) -> None:
    state = {
        "root": str(root.resolve()),
        "backend_pid": backend_pid,
        "vite_pid": vite_pid,
        "backend_port": backend_port,
        "frontend_port": frontend_port,
        "started_at": time.time(),
    }
    _launch_state_path(root).write_text(json.dumps(state, indent=2), encoding="utf-8")


def _remove_launch_state(root: Path) -> None:
    _launch_state_path(root).unlink(missing_ok=True)


def _first_available_port(start: int, blocked: set[int] | None = None) -> int:
    blocked = blocked or set()
    port = start
    while port in blocked or _port_in_use(port):
        port += 1
    return port


def _choose_launch_ports(*, dev_mode: bool) -> LaunchPorts:
    backend_port = _first_available_port(DEFAULT_BACKEND_PORT)
    if not dev_mode:
        return LaunchPorts(backend=backend_port)
    frontend_port = _first_available_port(DEFAULT_FRONTEND_PORT, {backend_port})
    return LaunchPorts(backend=backend_port, frontend=frontend_port)


def _child_process_kwargs() -> dict:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _frontend_env(api_port: int, app_port: int) -> dict[str, str]:
    env = os.environ.copy()
    env["DODGEBALL_API_PORT"] = str(api_port)
    env["DODGEBALL_APP_PORT"] = str(app_port)
    return env


def _print_port_notice(ports: LaunchPorts) -> None:
    if ports.backend != DEFAULT_BACKEND_PORT:
        print(f"Port {DEFAULT_BACKEND_PORT} is occupied; using API port {ports.backend}.")
    if ports.frontend is not None and ports.frontend != DEFAULT_FRONTEND_PORT:
        print(f"Port {DEFAULT_FRONTEND_PORT} is occupied; using app port {ports.frontend}.")


def _build_frontend(root: Path) -> None:
    print("Building frontend (first run)...")
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    result = subprocess.run(
        [npm, "--prefix", "frontend", "install", "--silent"],
        cwd=str(root),
    )
    if result.returncode != 0:
        print("Error: npm install failed. Make sure Node.js is installed.")
        sys.exit(1)
    result = subprocess.run(
        [npm, "--prefix", "frontend", "run", "build"],
        cwd=str(root),
    )
    if result.returncode != 0:
        print("Error: Frontend build failed.")
        sys.exit(1)
    print("Frontend built successfully.")


def _run_dev(root: Path) -> None:
    stopped = _stop_previous_launch(root)
    if stopped:
        print("Stopped previous Dodgeball Manager dev server.")
    ports = _choose_launch_ports(dev_mode=True)
    _print_port_notice(ports)
    assert ports.frontend is not None

    print("Starting Dodgeball Manager [DEV]")
    print(f"  API  -> http://localhost:{ports.backend}")
    print(f"  App  -> http://localhost:{ports.frontend}  (Vite HMR)")

    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    vite_proc = subprocess.Popen(
        [npm, "--prefix", "frontend", "run", "dev"],
        cwd=str(root),
        env=_frontend_env(ports.backend, ports.frontend),
        **_child_process_kwargs(),
    )
    _write_launch_state(
        root,
        backend_port=ports.backend,
        frontend_port=ports.frontend,
        backend_pid=os.getpid(),
        vite_pid=vite_proc.pid,
    )
    threading.Thread(
        target=_open_browser, args=(f"http://localhost:{ports.frontend}", 2.5), daemon=True
    ).start()

    try:
        uvicorn.run(
            "dodgeball_sim.server:app",
            host="127.0.0.1",
            port=ports.backend,
            log_level="info",
            reload=True,
        )
    finally:
        _terminate_pid(vite_proc.pid)
        _remove_launch_state(root)


def _run_prod(root: Path) -> None:
    stopped = _stop_previous_launch(root)
    if stopped:
        print("Stopped previous Dodgeball Manager server.")
    ports = _choose_launch_ports(dev_mode=False)
    _print_port_notice(ports)

    if Path("frontend/dist").exists():
        frontend_dist = Path("frontend/dist")
    else:
        frontend_dist = root / "frontend" / "dist"

    if not frontend_dist.exists():
        _build_frontend(root)

    print("Starting Dodgeball Manager...")
    _write_launch_state(
        root,
        backend_port=ports.backend,
        frontend_port=None,
        backend_pid=os.getpid(),
    )
    threading.Thread(
        target=_open_browser, args=(f"http://localhost:{ports.backend}",), daemon=True
    ).start()
    try:
        uvicorn.run(
            "dodgeball_sim.server:app",
            host="127.0.0.1",
            port=ports.backend,
            log_level="info",
        )
    finally:
        _remove_launch_state(root)


def main() -> None:
    dev_mode = os.environ.get("DODGEBALL_DEV", "").lower() in ("1", "true", "yes")
    root = _project_root()
    if dev_mode:
        _run_dev(root)
    else:
        _run_prod(root)


if __name__ == "__main__":
    main()
