"""MHY Scanner Py - 米哈游扫码登录器 Web版
FastAPI 主入口
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .config import init_config
from .routers import account, auth, scan, ws, config_route


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_config()
    yield


app = FastAPI(
    title="MHY Scanner",
    description="米哈游扫码登录器 - Web版",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(account.router)
app.include_router(auth.router)
app.include_router(scan.router)
app.include_router(ws.router)
app.include_router(config_route.router)

# 静态文件（前端）
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
