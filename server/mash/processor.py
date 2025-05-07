# server/mash/processor.py
import requests
import os
import base64
from typing import List, Dict
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

BEARER_TOKEN = os.getenv("SOOT_ACCESS_TOKEN")


class Metadata(BaseModel):
    imageURL: str
    instanceId: str
    filename: str | None = None
    spaceId: str
    operation: int

def process_metadata_entries(metadata_list: List[Metadata]) -> List[Dict]:
    results = []

    for meta in metadata_list:
        try:
            headers = {
                "Authorization": f"Bearer {BEARER_TOKEN}"
            }
            res = requests.get(meta.imageURL, headers=headers)
            res.raise_for_status()
            image_bytes = res.content
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            description = generate_description(meta)

            results.append({
                "metadata": meta.dict(),
                "imageBase64": image_base64,
                "description": description
            })

        except Exception as e:
            print(f"[Error] Failed to fetch image from {meta.imageURL}: {e}")
            continue

    return results



def generate_description(meta: Metadata) -> str:
    return f"Fake description for image '{meta.filename or meta.instanceId[:6]}' with op {meta.operation}"
