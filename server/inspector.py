import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

SOOT_API_URL = os.getenv("SOOT_API_URL")
SOOT_ACCESS_TOKEN = os.getenv("SOOT_ACCESS_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {SOOT_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

def introspect_type(type_name: str):
    query = """
    query IntrospectType($typeName: String!) {
      __type(name: $typeName) {
        name
        kind
        fields {
          name
          type {
            name
            kind
            ofType {
              name
              kind
            }
          }
        }
      }
    }
    """

    variables = {"typeName": type_name}

    response = requests.post(SOOT_API_URL, json={"query": query, "variables": variables}, headers=HEADERS)
    data = response.json()
    print(json.dumps(data, indent=2))
    return data

if __name__ == "__main__":
    introspect_type("SpacePublication")
