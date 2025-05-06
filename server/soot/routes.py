from fastapi import APIRouter
from .connector import (
    get_user_spaces,
    get_space_items,
    get_publication_snapshot_url
   
)

router = APIRouter()

@router.get("/spaces")
def list_spaces():
    return get_user_spaces()

@router.get("/spaces/{space_id}/items")
def list_space_items(space_id: str):
    return get_space_items(space_id)


@router.get("/publications/{publication_id}/snapshot")
def get_publication_snapshot(publication_id: str):
    return get_publication_snapshot_url(publication_id)
