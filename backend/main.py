from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import health, briefing
from config import settings

app = FastAPI(
    title="Port Assistant API",
    description="Product Marketing Productivity Assistant for Port.io",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(briefing.router, prefix="/api/briefing", tags=["briefing"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Port Assistant API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=True
    )
