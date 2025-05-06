from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mash.routes import router as mash_router 
from soot.routes import router as soot_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

app.include_router(mash_router, prefix="/api/mash", tags=["Mash"])
app.include_router(soot_router, prefix="/api/soot")
