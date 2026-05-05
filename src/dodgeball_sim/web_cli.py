import os
import sys
import socket
import subprocess
import uvicorn
import webbrowser
import threading
import time
from pathlib import Path


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def _project_root() -> Path:
    """Return the repo root (where frontend/ lives)."""
    # When running from source, __file__ is src/dodgeball_sim/web_cli.py
    candidate = Path(__file__).parent.parent.parent
    if (candidate / "frontend").exists():
        return candidate
    # Fallback: CWD (e.g. when installed as a package and run from project root)
    return Path.cwd()


def _open_browser(url: str, delay: float = 1.5) -> None:
    time.sleep(delay)
    webbrowser.open(url)


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
    if _port_in_use(8000):
        print("Backend already running — opening browser.")
        webbrowser.open("http://localhost:5173")
        return

    print("Starting Dodgeball Manager [DEV]")
    print("  API  → http://localhost:8000")
    print("  App  → http://localhost:5173  (Vite HMR)")

    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    vite_proc = subprocess.Popen(
        [npm, "--prefix", "frontend", "run", "dev"],
        cwd=str(root),
    )
    threading.Thread(
        target=_open_browser, args=("http://localhost:5173", 2.5), daemon=True
    ).start()

    try:
        uvicorn.run(
            "dodgeball_sim.server:app",
            host="127.0.0.1",
            port=8000,
            log_level="info",
            reload=True,
        )
    finally:
        vite_proc.terminate()


def _run_prod(root: Path) -> None:
    if _port_in_use(8000):
        print("Dodgeball Manager is already running. Opening browser...")
        webbrowser.open("http://localhost:8000")
        return

    # Resolve dist path — prefer CWD-relative so packaged installs work
    if Path("frontend/dist").exists():
        frontend_dist = Path("frontend/dist")
    else:
        frontend_dist = root / "frontend" / "dist"

    if not frontend_dist.exists():
        _build_frontend(root)

    print("Starting Dodgeball Manager...")
    threading.Thread(
        target=_open_browser, args=("http://localhost:8000",), daemon=True
    ).start()
    uvicorn.run(
        "dodgeball_sim.server:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )


def main() -> None:
    dev_mode = os.environ.get("DODGEBALL_DEV", "").lower() in ("1", "true", "yes")
    root = _project_root()
    if dev_mode:
        _run_dev(root)
    else:
        _run_prod(root)


if __name__ == "__main__":
    main()
