"""OC-Monitor v3.0 FastAPI entrypoint."""
from contextlib import asynccontextmanager
from pathlib import Path
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import settings
from app.database import init_db
from app.api.auth import router as auth_router
from app.api.config import router as config_router
from app.api.metrics import router as metrics_router
from app.api.agents import router as agents_router
from app.api.alerts import router as alerts_router


logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _cors_origins() -> list[str]:
    if settings.CORS_ORIGINS.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("./data").mkdir(exist_ok=True)
    Path(settings.LOG_DIR).mkdir(parents=True, exist_ok=True)
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Stopping %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description="Lightweight OpenClaw monitoring API.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

origins = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = f"/{settings.API_PREFIX.strip('/')}"
app.include_router(auth_router, prefix=api_prefix)
app.include_router(config_router, prefix=api_prefix)
app.include_router(metrics_router, prefix=api_prefix)
app.include_router(agents_router, prefix=api_prefix)
app.include_router(alerts_router, prefix=api_prefix)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": api_prefix,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
