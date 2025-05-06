from fastapi import APIRouter, Query

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


@router.get("/snapshots")
def list_snapshots(space_id: str = Query(...)):
    """
    Return snapshot URLs for all publications under the given space_id.
    Example usage: /api/soot/snapshots?space_id=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    """
    space_data = get_space_items(space_id)
    try:
        edges = space_data["data"]["getSpaceById"]["space"]["publications"]["edges"]
        publication_ids = [edge["node"]["id"] for edge in edges]
    except Exception as e:
        return {
            "error": "Failed to parse publication IDs",
            "details": str(e),
            "raw": space_data
        }

    snapshots = []
    for pub_id in publication_ids:
        snapshot = get_publication_snapshot_url(pub_id)
        if "snapshot_url" in snapshot:
            snapshots.append(snapshot)

    return snapshots