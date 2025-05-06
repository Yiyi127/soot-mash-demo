import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

SOOT_API_URL = os.getenv("SOOT_API_URL")
SOOT_ACCESS_TOKEN = os.getenv("SOOT_ACCESS_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {SOOT_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


def get_user_spaces():
    query = """
    query {
      viewer {
        spaces {
          id
          displayName
        }
      }
    }
    """
    response = requests.post(SOOT_API_URL, json={"query": query}, headers=HEADERS)
    return response.json()


def get_space_items(space_id: str):
    query = f"""
    query {{
      getSpaceById(request: {{ id: "{space_id}" }}) {{
        ... on GetSpaceByIdResult {{
          space {{
            publications {{
              edges {{
                node {{
                  id
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """
    response = requests.post(SOOT_API_URL, json={"query": query}, headers=HEADERS)
    data = response.json()
    print("GraphQL response:")
    print(json.dumps(data, indent=2))
    return data

