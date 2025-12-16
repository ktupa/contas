from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from contextlib import asynccontextmanager
import structlog
from app.config import settings
from app.routers import auth, employees, rubrics, competencies, payments, attachments, reports, maintenance, expenses, companies, signatures, fiscal
from app.jobs import start_scheduler, stop_scheduler


# Configurar logs estruturados
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento do ciclo de vida da aplicação"""
    logger.info("application_starting", environment=settings.ENVIRONMENT)
    
    # Iniciar scheduler de jobs
    start_scheduler()
    
    yield
    
    # Parar scheduler
    stop_scheduler()
    
    logger.info("application_shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    root_path="/api"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    import json
    error_details = exc.errors()
    logger.error(
        "validation_error",
        path=str(request.url.path),
        method=request.method,
        errors=json.dumps(error_details),
        body=str(exc.body)
    )
    # Print também para stdout
    print(f"\n=== VALIDATION ERROR ===")
    print(f"Path: {request.url.path}")
    print(f"Errors: {json.dumps(error_details, indent=2)}")
    print(f"Body: {exc.body}")
    print("=" * 50)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": error_details}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc)
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Health check
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "app": settings.APP_NAME
    }


# Routers
app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(rubrics.router)
app.include_router(competencies.router)
app.include_router(payments.router)
app.include_router(attachments.router)
app.include_router(reports.router)
app.include_router(maintenance.router)
app.include_router(expenses.router)
app.include_router(companies.router)
app.include_router(signatures.router)
app.include_router(fiscal.router)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }
