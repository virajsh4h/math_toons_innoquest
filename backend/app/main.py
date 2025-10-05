# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import generator

app = FastAPI(
    title="Math Toons API",
    description="API for generating personalized math explainer videos.",
    version="0.1.0"
)

# --- CRITICAL FIX: Add CORS Middleware ---
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- END CORS FIX ---

# Include router
app.include_router(generator.router, prefix="/api/v1", tags=["Video Generation"])

@app.get("/health", tags=["Health Check"])
def health_check():
    """
    Simple health check to confirm the API is running.
    """
    return {"status": "LETSGO (Health: ok)"}