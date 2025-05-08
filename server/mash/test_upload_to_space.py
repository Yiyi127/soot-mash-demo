import requests
from typing import List

SOOT_API = "https://api.soot.com/graphql"  
SOOT_ACCESS_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjU5MWYxNWRlZTg0OTUzNjZjOTgyZTA1MTMzYmNhOGYyNDg5ZWFjNzIiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiWm9leSBMaXUiLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jTDR6U1NIejRlQ0tZUElJMWJwMU5GMHp6cHdoZ2ZPcVhQSUxMVUVMZE1zZklKN3JRPXM5Ni1jIiwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL3Nvb3QtOTBkNTEiLCJhdWQiOiJzb290LTkwZDUxIiwiYXV0aF90aW1lIjoxNzQ2NTk4OTYxLCJ1c2VyX2lkIjoiMkxnU2Nld3Q2NGg1VWZneG5UcG9mZVJSMzU4MiIsInN1YiI6IjJMZ1NjZXd0NjRoNVVmZ3huVHBvZmVSUjM1ODIiLCJpYXQiOjE3NDY2OTEwMDgsImV4cCI6MTc0NjY5NDYwOCwiZW1haWwiOiJ4LXpvZXlAc29vdC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJnb29nbGUuY29tIjpbIjExNzY3MTI2MzcxNTQzMzcxMDY5MyJdLCJlbWFpbCI6WyJ4LXpvZXlAc29vdC5jb20iXX0sInNpZ25faW5fcHJvdmlkZXIiOiJnb29nbGUuY29tIn19.aK4t9bYfMuQgNPa3OT31xYD0Pd8dx1V7VGpXJrnCNMZeGVKHHtpXWv0Nl7xCcMrR9bSvUkUUNszvZFW0HxRLky4aEq-jfrHJQGK-0XEKHjrL2lSJdRp7HNsaB_oYfHwbhLxT1gOgntDUvg2cy78zlle7OeWGItptJF4ivwbNALYNVtxib2uvdcUJbjfDco03_p0tgy-SIEAZBhRAW60dhFLZSmidwclgYwLReZPXs0FXorwT8uXUT27V47b951WivyuMwMNd6oOWaLq1IIqjTeWEab3AbTZGAwxwlDGrl6H1lBY_gOukVoG-9Sli4Ladg8fAtdncq73Lv7gbdXotVA"  # 这里需要填入你的实际访问令牌

def create_upload_intent(space_id: str) -> str:
    """Create an upload intent for a given space."""
    payload = {
        "query": """
        mutation CreateUploadIntent($request: CreateUploadIntentRequest!) {
          createUploadIntent(request: $request) {
            __typename
            ... on CreateUploadIntentResult { uploadIntent { id } }
            ... on PermissionDeniedError { reason }
            ... on NotFoundError { entity }
          }
        }
        """,
        "variables": {"request": {"source": {"url": {}}, "destination": {"space": space_id}}},
        "operationName": "CreateUploadIntent"
    }
    headers = {"Authorization": f"Bearer {SOOT_ACCESS_TOKEN}", "Content-Type": "application/json"}

    print(f"Creating upload intent for space '{space_id}'...")
    response = requests.post(SOOT_API, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()
    if 'errors' in result:
        raise Exception(f"GraphQL errors: {result['errors']}")

    intent = result['data']['createUploadIntent'].get('uploadIntent', {})
    intent_id = intent.get('id')
    if not intent_id:
        raise Exception(f"Failed to extract uploadIntent ID: {result}")

    print(f"🔑 Upload intent created: ID={intent_id}")
    return intent_id

def upload_image_from_url(intent_id: str, image_urls: List[str]):
    """Upload an image to SOOT by URL using an existing upload intent."""
    payload = {
        "query": """
        mutation UploadFromUrl($request: UploadFromUrlRequest!) {
          uploadFromUrl(request: $request) {
            __typename
            ... on UploadFromUrlResult { __typename }
            ... on PermissionDeniedError { reason }
            ... on ValidationError { field reason }
          }
        }
        """,
        "variables": {"request": {"uploadIntent": intent_id, "urls": image_urls}},
        "operationName": "UploadFromUrl"
    }
    headers = {"Authorization": f"Bearer {SOOT_ACCESS_TOKEN}", "Content-Type": "application/json"}

    print(f"Uploading image from URLs...")
    response = requests.post(SOOT_API, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()
    if 'errors' in result:
        raise Exception(f"GraphQL errors: {result['errors']}")

    typename = result['data']['uploadFromUrl']['__typename']
    if typename != "UploadFromUrlResult":
        raise Exception(f"Upload failed: {typename}")

    print("✓ Upload request accepted; SOOT will fetch the image.")

def complete_upload_intent(intent_id: str, count: int = 1):
    """Complete the upload intent once files are uploaded."""
    payload = {
        "query": """
        mutation CompleteUploadIntent($request: CompleteUploadIntentRequest!) {
          completeUploadIntent(request: $request) {
            __typename
            ... on CompleteUploadIntentResult { uploadIntent { id } }
            ... on ValidationError { field reason }
          }
        }
        """,
        "variables": {"request": {"uploadIntent": intent_id, "filesUploaded": count}},
        "operationName": "CompleteUploadIntent"
    }
    headers = {"Authorization": f"Bearer {SOOT_ACCESS_TOKEN}", "Content-Type": "application/json"}

    print(f"Completing upload intent '{intent_id}' with {count} file(s)...")
    response = requests.post(SOOT_API, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()
    if 'errors' in result:
        raise Exception(f"GraphQL errors: {result['errors']}")

    print(f"✓ Upload intent '{intent_id}' completed.")

def test_upload_image():
    """Test uploading an image to SOOT."""
    space_id = "bae1c7d4-f130-450b-8c3e-a359caa885a0"
    
    image_url = "https://images.unsplash.com/photo-1615789591457-74a63395c990?q=80&w=1074&auto=format&fit=crop"
    
    try:
        intent_id = create_upload_intent(space_id)
        
        upload_image_from_url(intent_id, [image_url])
        
        complete_upload_intent(intent_id)
        
        print("✅ Test completed successfully! The image should now be in your space.")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_upload_image()