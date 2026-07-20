import sys
from pathlib import Path

# Register workspace root so `ai` package is importable as `ai.xxx`
_ROOT_PATH = str(Path(__file__).resolve().parent.parent)
if _ROOT_PATH not in sys.path:
    sys.path.insert(0, _ROOT_PATH)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# ---------------------------------
# Routers
# ---------------------------------

from monitoring_api import router as monitoring_router
from freshness_api import router as freshness_router
from volume_api import router as volume_router
from lineage_api import router as lineage_router
from alerts_api import router as alerts_router
from metrics_api import router as metrics_router
from agents_api import router as agents_router


app = FastAPI(
    title="ETL Metadata Repository API — Tusk Copilot",
    description="Centralized APIs for ETL Monitoring, Freshness, Volume, Lineage, Metrics, Alerts and the Tusk Multi-Agent AI Copilot.",
    version="2.0.0"
)

# ---------------------------------
# CORS Configuration
# ---------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Change in Production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------
# Register Routers
# ---------------------------------

app.include_router(monitoring_router)
app.include_router(freshness_router)
app.include_router(volume_router)
app.include_router(lineage_router)
app.include_router(alerts_router)
app.include_router(metrics_router)
app.include_router(agents_router)


# ---------------------------------
# System Metrics Endpoint
# ---------------------------------

@app.get("/metrics", tags=["Metrics"], summary="Get System Metrics")
def get_system_metrics():
    from monitoring_api import service as monitoring_service
    return monitoring_service.get_metrics()


from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

# Mount static frontend assets
frontend_dir = Path(_ROOT_PATH) / "frontend"
app.mount("/ui", StaticFiles(directory=str(frontend_dir)), name="ui")


# ---------------------------------
# Root Endpoint (Redirect to Frontend)
# ---------------------------------

@app.get("/")
def root():
    return RedirectResponse(url="/ui/index.html")


# ---------------------------------
# Health Endpoint
# ---------------------------------

@app.get("/health")
def health():

    return {
        "success": True,
        "status": "UP",
        "service": "ETL Metadata Repository API"
    }


# ---------------------------------
# Test Webhook Receiver Endpoint
# ---------------------------------

@app.post("/test-webhook-receiver", tags=["Test"])
def test_webhook_receiver(payload: dict):
    import json
    import logging
    log = logging.getLogger("app")
    log.info(f"Test Webhook received: {json.dumps(payload, indent=2)}")
    return {"status": "received", "payload": payload}


# ---------------------------------
# Application Entry Point
# ---------------------------------

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )