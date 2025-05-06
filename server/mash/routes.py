from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
from mash.processor import process_entries

router = APIRouter()

class SootEntry(BaseModel):
    imageURL: str
    instanceId: str
    filename: str | None
    spaceId: str
    operation: int

@router.post("/mash/process-entries")
async def receive_entries(entries: List[SootEntry]):
    return await process_entries(entries)
