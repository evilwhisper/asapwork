from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text

from backend.config import ALLOWED_ORIGINS, APP_VERSION, DEPLOY_MODE
from backend.database import AsyncSessionLocal, Base, engine
from backend.middleware.auth import BasicAuthMiddleware
from backend.routers import applications, jobs, notifications, profile, settings
from backend.scheduler import scheduler, setup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start scheduler then register jobs from DB config
    scheduler.start()
    await setup_scheduler()

    yield

    scheduler.shutdown(wait=False)
    await engine.dispose()


app = FastAPI(
    title="Job Agent API",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(BasicAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(settings.router)
app.include_router(notifications.router)


@app.get("/api/health")
async def health():
    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass
    return {"status": "ok", "mode": DEPLOY_MODE, "version": APP_VERSION, "db_connected": db_ok}


# Serve built frontend if it exists (launcher / exe mode — no separate Vite server needed)
_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(_dist / "index.html")
