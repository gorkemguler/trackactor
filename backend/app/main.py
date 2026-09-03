"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .database import init_db
from .routers import actors, capture, cases, contacts, interactions, lookup, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="trackactor",
    version=__version__,
    summary="Threat-actor engagement tracker for CTI & SOC analysts",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"chrome-extension://.*|moz-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router)
app.include_router(actors.router)
app.include_router(contacts.router)
app.include_router(interactions.router)
app.include_router(lookup.router)
app.include_router(capture.router)
app.include_router(stats.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "version": __version__}


@app.get("/api/meta/enums", tags=["meta"])
def enums():
    """Enum values for the frontend dropdowns."""
    from . import schemas

    return {
        "actor_types": schemas.ACTOR_TYPES,
        "channel_types": schemas.CHANNEL_TYPES,
        "case_statuses": schemas.CASE_STATUSES,
        "priorities": schemas.PRIORITIES,
        "directions": schemas.DIRECTIONS,
    }
