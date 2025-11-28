from fastapi import FastAPI
from app.db.database import engine
from app.db.base import Base

app = FastAPI(
    title="Builder Operating System",
    description="API for managing operators and principals in the commercial real estate industry",
    version="0.1.0"
)


@app.on_event("startup")
def on_startup():
    """
    Run on application startup.
    Creates database tables if they don't exist.
    """
    # Import models to ensure they're registered with Base
    from app.models import Operator, Principal

    # Note: In production, use Alembic migrations instead
    # This is kept here for development convenience
    # Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root():
    return {
        "message": "Builder Operating System API",
        "status": "running",
        "version": "0.1.0"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
