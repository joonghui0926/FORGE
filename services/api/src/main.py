from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import orders, captures, jobs, webhooks, deliveries, health
from .migrations import apply_migrations


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("FORGE_AUTO_MIGRATE", "false").lower() == "true":
        apply_migrations()
    yield


app = FastAPI(title="FORGE API", version="0.2.0", lifespan=lifespan)

allowed_origins = {
    "http://localhost:3000",
    *(value.strip() for value in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if value.strip()),
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router)
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(captures.router, prefix="/captures", tags=["captures"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(deliveries.router, prefix="/deliveries", tags=["deliveries"])
