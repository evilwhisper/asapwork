"""
Build a standalone Job Agent.exe using PyInstaller.

Usage:
    python build_exe.py

Requirements:
    pip install pyinstaller
    npm must be installed for frontend build step.

Output:
    dist/Job Agent.exe   (Windows)
    dist/Job Agent       (Mac/Linux)
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def run(cmd, **kw):
    print(f"  > {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, check=True, **kw)


def build_frontend():
    frontend = ROOT / "frontend"
    print("\n[1/3] Building frontend...")
    run(["npm", "install", "--silent"], cwd=frontend)
    run(["npm", "run", "build"], cwd=frontend)
    print("  Frontend built to frontend/dist")


def collect_hidden_imports():
    return [
        "backend",
        "backend.main",
        "backend.config",
        "backend.database",
        "backend.models",
        "backend.schemas",
        "backend.scheduler",
        "backend.middleware.auth",
        "backend.routers.profile",
        "backend.routers.jobs",
        "backend.routers.applications",
        "backend.routers.settings",
        "backend.routers.notifications",
        "backend.scrapers.base",
        "backend.scrapers.seek",
        "backend.scrapers.indeed_au",
        "backend.scrapers.linkedin_au",
        "backend.scrapers.jora",
        "backend.services.ai_service",
        "backend.services.document_service",
        "backend.services.matching_service",
        "backend.services.submission_service",
        "backend.services.token_counter",
        "aiosqlite",
        "sqlalchemy.dialects.sqlite",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.lifespan.on",
        "passlib.handlers.bcrypt",
    ]


def build_exe():
    print("\n[2/3] Running PyInstaller...")

    hidden = []
    for h in collect_hidden_imports():
        hidden += ["--hidden-import", h]

    datas = [
        f"frontend/dist{os.pathsep}frontend/dist",
        f"backend{os.pathsep}backend",
    ]
    data_args = []
    for d in datas:
        data_args += ["--add-data", d]

    icon = ROOT / "frontend" / "public" / "icon.ico"
    icon_args = ["--icon", str(icon)] if icon.exists() else []

    run([
        sys.executable, "-m", "PyInstaller",
        "run.py",
        "--name", "Job Agent",
        "--onefile",
        "--clean",
        "--noconfirm",
        *hidden,
        *data_args,
        *icon_args,
        "--collect-all", "uvicorn",
        "--collect-all", "fastapi",
        "--collect-all", "starlette",
    ])


def done():
    exe = "Job Agent.exe" if sys.platform == "win32" else "Job Agent"
    path = ROOT / "dist" / exe
    print(f"\n[3/3] Done!")
    print(f"  Output: {path}")
    print(f"\n  Distribute the single file — no Python needed.")
    print(f"  First launch downloads Chromium (~120 MB) once.")


if __name__ == "__main__":
    build_frontend()
    build_exe()
    done()
