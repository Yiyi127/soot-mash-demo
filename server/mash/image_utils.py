import requests
import os
from dotenv import load_dotenv
import base64

load_dotenv()

SOOT_ACCESS_TOKEN = os.getenv("SOOT_ACCESS_TOKEN")

def fetch_image_as_base64(url: str) -> str | None:
    try:
        res = requests.get(url, headers={
            "Authorization": f"Bearer {SOOT_ACCESS_TOKEN}",
            "Accept": "image/*"
        }, timeout=10)
        res.raise_for_status()
        encoded = base64.b64encode(res.content).decode("utf-8")
        return encoded
    except Exception as e:
        print(f"[SOOT] ❌ Fetch failed for {url}: {e}")
        return None
