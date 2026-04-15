import logging
import time
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings
from app.db import init_db
from app.routes import auth_router, notes_router
from app.auth.dependencies import get_current_user

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Notes API with Keycloak Authentication", version="1.0")

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, max_age=3600)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s"
    )
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.on_event("startup")
async def startup():
    logger.info("Starting up Notes API...")
    init_db()


@app.get("/")
def root():
    return {"message": "Notes API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


app.include_router(auth_router)
app.include_router(notes_router, prefix="/api")
