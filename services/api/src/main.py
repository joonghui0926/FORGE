from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import orders, captures, jobs, webhooks, deliveries, health

app = FastAPI(title="FORGE API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # replaced with APP_BASE_URL in production
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
