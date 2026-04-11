from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from api import datasets, copilot

# Check if Redis cache is available for the health check
try:
    from cache import REDIS_AVAILABLE
except ImportError:
    REDIS_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    init_db()
    
    yield  
    
    
app = FastAPI(title="Data Copilot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# modular routes
app.include_router(datasets.router)
app.include_router(copilot.router)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "redis": REDIS_AVAILABLE
    }