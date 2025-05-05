import os
import requests
from dotenv import load_dotenv

load_dotenv()

SOOT_API_URL = os.getenv("SOOT_API_URL")
SOOT_ACCESS_TOKEN = os.getenv("SOOT_ACCESS_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {SOOT_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

def fetch_user_spaces():
    query = """
    query {
      viewer {
        spaces {
          id
        }
      }
    }
    """
    response = requests.post(SOOT_API_URL, json={"query": query}, headers=HEADERS)
    return response.json()
