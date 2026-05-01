import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.db import Base, engine
from backend.routers import costs, jobs, printers, spools
from backend.scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="PrintFarm Tracker API", version="0.1.0", lifespan=lifespan)

app.include_router(spools.router, prefix="/api")
app.include_router(printers.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(costs.router, prefix="/api")

# Serve the built React frontend from /frontend/dist
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        return FileResponse(FRONTEND_DIST / "index.html")
