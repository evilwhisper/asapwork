"""Entry point for PyInstaller exe."""
import multiprocessing
import os
import sys
import threading
import time
import webbrowser

# PyInstaller sets sys._MEIPASS when running from exe
if getattr(sys, "frozen", False):
    # Ensure backend can be imported from the bundle
    bundle_dir = sys._MEIPASS
    sys.path.insert(0, bundle_dir)
    # Point data dirs to alongside the exe
    exe_dir = os.path.dirname(sys.executable)
    os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{exe_dir}/jobagent.db")
    os.environ.setdefault("UPLOAD_DIR", os.path.join(exe_dir, "uploads"))
    os.environ.setdefault("DEPLOY_MODE", "local")

PORT = int(os.environ.get("PORT", 8000))


def _open_browser():
    time.sleep(3)
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    threading.Thread(target=_open_browser, daemon=True).start()
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=PORT, log_level="warning")
