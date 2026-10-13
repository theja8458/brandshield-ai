from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import close_database, ping_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    yield
    # Shutdown actions
    close_database()


app = FastAPI(
    title="BrandShield AI Backend",
    version="0.1.0",
    description="Digital Risk Protection Prototype API for Social & App Monitoring",
    lifespan=lifespan,
)

from app.api.auth import router as auth_router
from app.api.deps import get_current_user
from app.api.brands import router as brands_router
from app.api.detection import router as detection_router
from app.api.sources import router as sources_router
from app.api.social import router as social_router
from app.api.apps import router as apps_router
from app.api.dashboard import router as dashboard_router
from app.api.investigations import router as investigations_router
from app.api.campaigns import router as campaigns_router

# CORS configuration restricted to configured frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication router (includes public /login, protected /me & /logout, and admin /users)
app.include_router(auth_router)

# Protected operational routers: require authenticated active user
app.include_router(brands_router, dependencies=[Depends(get_current_user)])
app.include_router(detection_router, dependencies=[Depends(get_current_user)])
app.include_router(sources_router, dependencies=[Depends(get_current_user)])
app.include_router(social_router, dependencies=[Depends(get_current_user)])
app.include_router(apps_router, dependencies=[Depends(get_current_user)])
app.include_router(dashboard_router, dependencies=[Depends(get_current_user)])
app.include_router(investigations_router, dependencies=[Depends(get_current_user)])
app.include_router(campaigns_router, dependencies=[Depends(get_current_user)])


@app.get("/health", tags=["System"])
def process_health():
    """
    Process health check. Returns immediate 200 OK if FastAPI process is alive.
    Used by container runners and load balancers.
    """
    return {
        "status": "ok",
        "service": "brandshield-ai-backend",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/api/v1/health", tags=["System"])
def api_readiness(response: Response):
    """
    API & Database readiness check.
    Pings MongoDB Atlas. Does NOT claim readiness if database is unreachable.
    """
    is_connected, message = ping_database()
    if is_connected:
        return {
            "status": "ready",
            "database": "connected",
            "database_name": settings.DATABASE_NAME,
            "environment": settings.ENVIRONMENT,
        }

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "degraded",
        "database": "disconnected",
        "detail": message,
        "environment": settings.ENVIRONMENT,
    }
