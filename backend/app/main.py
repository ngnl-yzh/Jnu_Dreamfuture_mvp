from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, tokens

app = FastAPI(title=get_settings().app_name)

app.include_router(auth.router)
app.include_router(tokens.router)

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
