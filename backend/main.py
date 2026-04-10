from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from api import datasets, copilot

# Check if Redis cache is available for the health check
try:
    from cache import REDIS_AVAILABLE
except:
    REDIS_AVAILABLE = False

app = FastAPI(title="Data Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

#  Plug in the modular routes we just created
app.include_router(datasets.router)
app.include_router(copilot.router)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "redis": REDIS_AVAILABLE
    }