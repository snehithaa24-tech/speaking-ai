from contextlib import asynccontextmanager
from datetime import datetime, timezone
import time
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware, rate_limiter
from app.database.session import init_db, close_db
from app.api.v1 import sessions, knowledge, auth, websocket


logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SAHAYAK AI backend...")
    await init_db()

    from app.database.session import AsyncSessionLocal
    from app.services.knowledge import KnowledgeService

    async with AsyncSessionLocal() as db:
        knowledge_service = KnowledgeService(db)
        await knowledge_service.seed_initial_data()

    logger.info("Database initialized and seeded")

    yield

    logger.info("Shutting down SAHAYAK AI backend...")
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multilingual Real-Time Voice Assistant API",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Attach rate limiter to app.state for test accessibility
app.state.rate_limiter = rate_limiter

# Middleware registration order: RateLimitMiddleware is added first, CORSMiddleware is added second.
# In Starlette, the last added middleware executes outermost.
# This ensures CORSMiddleware wraps RateLimitMiddleware and attaches CORS headers to HTTP 429 responses.
app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc) if settings.DEBUG else None},
    )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
app.include_router(knowledge.router, prefix="/api/v1", tags=["knowledge"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(websocket.router, tags=["websocket"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        reload=settings.DEBUG,
    )