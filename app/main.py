from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine
from app.db.base import Base

# Import routers
from app.api import operators, deals, principals, documents, underwriting, funds

app = FastAPI(
    title="Builder Operating System",
    description="API for managing operators and principals in the commercial real estate industry",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """
    Run on application startup.
    Creates database tables if they don't exist.
    """
    # Import all models to ensure they're registered with Base
    from app.models import Operator, Principal, Deal, DealDocument, DealUnderwriting, Memo, Fund

    # Note: In production, use Alembic migrations instead
    # This is kept here for development convenience
    # Base.metadata.create_all(bind=engine)


# Include routers
app.include_router(operators.router, prefix="/api")
app.include_router(deals.router, prefix="/api")
app.include_router(principals.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(underwriting.router, prefix="/api")
app.include_router(funds.router, prefix="/api")


@app.get("/")
def read_root():
    return {
        "message": "Builder Operating System API",
        "status": "running",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
