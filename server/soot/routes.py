from fastapi import APIRouter
from .connector import fetch_user_spaces

router = APIRouter()

@router.get("/spaces")
def get_spaces():
    return fetch_user_spaces()

