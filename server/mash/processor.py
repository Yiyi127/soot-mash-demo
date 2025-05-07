import requests
import os
import base64
import mimetypes
import threading
import json
from typing import List, Dict
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

BEARER_TOKEN = os.getenv("SOOT_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL_NAME)

description_cache: dict[str, dict] = {}
cache_lock = threading.Lock()

class Metadata(BaseModel):
    imageURL: str
    instanceId: str
    filename: str | None = None
    spaceId: str
    operation: int

def process_metadata_entries(metadata_list: List[Metadata]) -> List[Dict]:
    frontend_payloads = []

    for meta in metadata_list:
        try:
            print(f"[📥] Fetching image for: {meta.filename or meta.instanceId[:6]}")
            headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
            res = requests.get(meta.imageURL, headers=headers)
            res.raise_for_status()
            image_bytes = res.content
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            frontend_payloads.append({
                "metadata": meta.dict(),
                "imageBase64": image_base64
            })

            print(f"[📤] Payload ready for frontend: {meta.filename or meta.instanceId[:6]}")

            threading.Thread(
                target=_generate_and_cache_description,
                args=(meta, image_base64)
            ).start()

        except Exception as e:
            print(f"[❌] Failed to process {meta.filename or meta.instanceId[:6]}: {e}")
            continue

    print(f"[✅] Total payloads returned: {len(frontend_payloads)}")
    return frontend_payloads

def _generate_and_cache_description(meta: Metadata, image_base64: str):
    try:
        print(f"[⏳] Starting description generation for {meta.instanceId[:6]}")
        description, raw_response = generate_description(image_base64, meta)
        tags = generate_tags(image_base64, meta)

        record = {
            "instanceId": meta.instanceId,
            "metadata": meta.dict(),
            "imageBase64": image_base64,
            "description": description,
            "tags": tags,
            "rawResponse": raw_response
        }

        with cache_lock:
            description_cache[meta.instanceId] = record
        print(f"[✅] Cached description for {meta.instanceId[:6]}")

    except Exception as e:
        print(f"[⚠️] Gemini error for {meta.instanceId[:6]}: {e}")

def generate_description(image_base64: str, meta: Metadata) -> tuple[str, str]:
    print(f"[🧠] Generating: {meta.filename or meta.instanceId[:6]}")
    try:
        image_bytes = base64.b64decode(image_base64)
        mime_type = mimetypes.guess_type(meta.filename or "")[0] or "image/png"

        response = model.generate_content([
            {"mime_type": mime_type, "data": image_bytes},
            {"text": "Describe this image in one short, clear sentence that captures the main subject and scene."}
        ])

        description = response.text.strip()
        print(f"[🎯] Gemini result for {meta.instanceId[:6]}: {description}")
        return description, response.text

    except Exception as e:
        print(f"[💥] Description generation failed for {meta.instanceId[:6]}: {e}")
        return "Failed to generate description", ""

def generate_tags(image_base64: str, meta: Metadata) -> List[str]:
    print(f"[🏷️] Tagging: {meta.filename or meta.instanceId[:6]}")
    try:
        image_bytes = base64.b64decode(image_base64)
        mime_type = mimetypes.guess_type(meta.filename or "")[0] or "image/png"

        response = model.generate_content([
            {"mime_type": mime_type, "data": image_bytes},
            {"text": "List 3 to 5 concise, lowercase tags that best describe the image content. Return only a JSON array."}
        ])

        tags_text = response.text.strip()
        if tags_text.startswith("["):
            tags = json.loads(tags_text)
            print(f"[🏷️] Tags parsed: {tags}")
            return tags
        else:
            print(f"[⚠️] Tag format unexpected: {tags_text}")
            return []

    except Exception as e:
        print(f"[💥] Tag generation failed for {meta.instanceId[:6]}: {e}")
        return []

def get_all_cached_descriptions() -> List[Dict]:
    with cache_lock:
        return list(description_cache.values())
