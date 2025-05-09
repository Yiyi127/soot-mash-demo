from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path
from mash.routes import router as mash_router 
from soot.routes import router as soot_router
from auth.routes import router as auth_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# 添加路由器
app.include_router(mash_router, prefix="/api/mash", tags=["Mash"])
app.include_router(soot_router, prefix="/api/soot", tags=["Soot"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

# 配置静态文件
# 尝试找到 client 目录的路径
client_dir = Path("../client")
if not client_dir.exists():
    # 尝试其他可能的位置
    client_dir = Path("./client")
    if not client_dir.exists():
        # 如果都找不到，使用绝对路径
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        client_dir = project_root / "client"

if client_dir.exists():
    print(f"[🌐] Serving static files from: {client_dir.absolute()}")
    app.mount("/", StaticFiles(directory=str(client_dir), html=True), name="static")
else:
    print(f"[⚠️] Warning: Client directory not found at {client_dir.absolute()}. Static files will not be served.")