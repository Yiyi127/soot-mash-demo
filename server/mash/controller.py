from fastapi import APIRouter
from typing import Dict

router = APIRouter()


@router.post("/")
def run_mash() -> Dict:
    return {
        "status": "success",
        "message": "Mash pipeline mock triggered!",
        "data": {
            "style_image_id": "abc123",
            "subject_image_id": "xyz456",
            "prompt": "Apply the style of image abc123 to the subject of xyz456"
        }
    }
