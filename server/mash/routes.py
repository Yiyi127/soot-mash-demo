# server/mash/routes.py
from fastapi import APIRouter
from typing import List
from .processor import Metadata, process_metadata_entries

router = APIRouter()

@router.post("/process-entries")
def process_entries(metadata_list: List[Metadata]):
    return process_metadata_entries(metadata_list)
