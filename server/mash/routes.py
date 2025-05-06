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

# ✅ This wrapper matches the structure `{ "entries": [...] }`
class SootEntryList(BaseModel):
    entries: List[SootEntry]

@router.post("/process-entries")
async def receive_entries(entry_list: SootEntryList):
    return await process_entries(entry_list.entries)
