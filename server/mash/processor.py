# server/mash/processor.py
import requests
import os
import base64
from typing import List, Dict
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai


load_dotenv()

BEARER_TOKEN = os.getenv("SOOT_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')


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

            description = generate_description(image_base64, meta)

            results.append({
                "metadata": meta.dict(),
                "imageBase64": image_base64,
                "description": description
            })

        except Exception as e:
            print(f"[Error] Failed to fetch image from {meta.imageURL}: {e}")
            continue

    return results

def generate_description(image_base64: str, meta: Metadata) -> str:
    print(f"[Debug] Base64 preview: {image_base64[:100]}...")

    try:
        image_bytes = base64.b64decode(image_base64)

        response = model.generate_content([
            {
                "mime_type": "image/png",  
                "data": image_bytes
            },
            {
                "text": "Please describe this image in one short sentence."
            }
        ])

        description = response.text.strip()
        print(f"[Gemini] Description: {description}")

        return description

    except Exception as e:
        print(f"[Error] Gemini API failed: {e}")
        return f"Error generating description for image '{meta.filename or meta.instanceId[:6]}'"