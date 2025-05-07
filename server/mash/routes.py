from fastapi import APIRouter
from typing import List
from .processor import Metadata, process_metadata_entries, get_all_cached_descriptions

router = APIRouter()

@router.post("/process-entries")
def process_entries(metadata_list: List[Metadata]):
    print(f"[🌐] Received metadata batch: {len(metadata_list)} entries")
    return process_metadata_entries(metadata_list)

@router.get("/descriptions")
def get_descriptions():
    print(f"[📦] Fetching cached descriptions...")
    return get_all_cached_descriptions()
