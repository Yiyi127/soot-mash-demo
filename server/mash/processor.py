from mash.image_utils import fetch_image_as_base64
from typing import List
from pydantic import BaseModel

class SootEntry(BaseModel):
    imageURL: str
    instanceId: str
    filename: str | None
    spaceId: str
    operation: int

async def process_entries(entries: List[SootEntry]):
    print(f"[SOOT] ✅ Received {len(entries)} entries")

    results = []
    for entry in entries:
        base64_img = fetch_image_as_base64(entry.imageURL)
        print(f"[SOOT] Processed {entry.imageURL} => {len(base64_img or '')} bytes")
        results.append({
            "metadata": entry.dict(),
            "imageBase64": base64_img,
        })

    return {"payloads": results}
