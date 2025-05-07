import requests
import os
import base64
import mimetypes
from typing import List, Dict
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

BEARER_TOKEN = os.getenv("SOOT_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


genai.configure(api_key=GEMINI_API_KEY)
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
model = genai.GenerativeModel(GEMINI_MODEL_NAME)

class Metadata(BaseModel):
    imageURL: str
    instanceId: str
    filename: str | None = None
    spaceId: str
    operation: int

def process_metadata_entries(metadata_list: List[Metadata]) -> tuple[List[Dict], List[Dict]]:
    frontend_payloads = []
    backend_full_records = []

    for meta in metadata_list:
        try:
            headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
            res = requests.get(meta.imageURL, headers=headers)
            res.raise_for_status()

            image_bytes = res.content
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            description, raw_response = generate_description(image_base64, meta)

            frontend_payloads.append({
                "metadata": meta.dict(),
                "imageBase64": image_base64
            })

            backend_full_records.append({
                "metadata": meta.dict(),
                "imageBase64": image_base64,
                "description": description,
                "rawResponse": raw_response
            })

        except Exception as e:
            print(f"[Error] Failed to process image ({meta.filename or meta.instanceId[:6]}): {e}")
            continue

    return frontend_payloads, backend_full_records


def generate_description(image_base64: str, meta: Metadata) -> tuple[str, str]:
    print(f"[Debug] Processing: {meta.filename or meta.instanceId[:6]}")
    print(f"[Debug] Base64 preview: {image_base64[:100]}...")

    try:
        image_bytes = base64.b64decode(image_base64)

        mime_type = mimetypes.guess_type(meta.filename or "")[0] or "image/png"

        response = model.generate_content([
            {"mime_type": mime_type, "data": image_bytes},
            {"text": "Describe this image in one short, clear sentence that captures the main subject and scene."}
        ])

        description = response.text.strip()
        print(f"[Gemini] {meta.filename or meta.instanceId[:6]} → {description}")

        return description, response.text

    except Exception as e:
        print(f"[Error] Gemini API failed for {meta.filename or meta.instanceId[:6]}: {e}")
        return f"Error generating description for image '{meta.filename or meta.instanceId[:6]}'", ""
