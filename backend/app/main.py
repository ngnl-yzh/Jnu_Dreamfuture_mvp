import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, instances, mvps, reviews, tokens

_idle_stop = threading.Event()


def _idle_cleanup_loop():
    from app.database import get_sessionmaker
    from app.routers.instances import stop_idle_instances

    while not _idle_stop.wait(300):  # 5분 간격
        with get_sessionmaker()() as db:
            stop_idle_instances(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if get_settings().sandbox_enabled:
        threading.Thread(target=_idle_cleanup_loop, daemon=True).start()
    yield
    _idle_stop.set()


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)

app.include_router(auth.router)
app.include_router(tokens.router)
app.include_router(mvps.router)
app.include_router(instances.router)
app.include_router(reviews.router)

# CORS는 로컬 프론트엔드만 최소 허용 (운영 시 도메인 교체)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
