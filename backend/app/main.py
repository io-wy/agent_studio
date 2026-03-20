"""Main FastAPI application"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.endpoints import tenant, dataset, training, agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tenant.router, prefix="/api/v1")
app.include_router(tenant.project_router, prefix="/api/v1")
app.include_router(dataset.router, prefix="/api/v1")
app.include_router(training.router, prefix="/api/v1")
app.include_router(training.model_router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")
app.include_router(agent.revision_router, prefix="/api/v1")
app.include_router(agent.run_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
