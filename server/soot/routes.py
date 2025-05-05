from fastapi import APIRouter, HTTPException
from .connector import fetch_user_spaces

router = APIRouter()

@router.get("/spaces")
def get_spaces():
    return fetch_user_spaces()

@router.get("/spaces/{space_id}/items")
def get_items_from_space(space_id: str):
    data = fetch_user_spaces()

    if "data" not in data:
        raise HTTPException(status_code=500, detail="GraphQL error: " + str(data.get("errors", "Unknown error")))

    matched = next((s for s in data["data"]["viewer"]["spaces"] if s["id"] == space_id), None)
    if matched is None:
        raise HTTPException(status_code=404, detail=f"Space with id {space_id} not found")

    return {"space_id": space_id}
