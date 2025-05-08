# upload_utils.py

import requests
import base64
import os
import json
from typing import List, Dict, Optional, Union, Tuple

# Global configuration
SOOT_API = "https://api.soot.com/graphql"
SOOT_ACCESS_TOKEN="eyJhbGciOiJSUzI1NiIsImtpZCI6IjU5MWYxNWRlZTg0OTUzNjZjOTgyZTA1MTMzYmNhOGYyNDg5ZWFjNzIiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiWm9leSBMaXUiLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jTDR6U1NIejRlQ0tZUElJMWJwMU5GMHp6cHdoZ2ZPcVhQSUxMVUVMZE1zZklKN3JRPXM5Ni1jIiwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL3Nvb3QtOTBkNTEiLCJhdWQiOiJzb290LTkwZDUxIiwiYXV0aF90aW1lIjoxNzQ2NTk4OTYxLCJ1c2VyX2lkIjoiMkxnU2Nld3Q2NGg1VWZneG5UcG9mZVJSMzU4MiIsInN1YiI6IjJMZ1NjZXd0NjRoNVVmZ3huVHBvZmVSUjM1ODIiLCJpYXQiOjE3NDY2OTg1MjYsImV4cCI6MTc0NjcwMjEyNiwiZW1haWwiOiJ4LXpvZXlAc29vdC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJnb29nbGUuY29tIjpbIjExNzY3MTI2MzcxNTQzMzcxMDY5MyJdLCJlbWFpbCI6WyJ4LXpvZXlAc29vdC5jb20iXX0sInNpZ25faW5fcHJvdmlkZXIiOiJnb29nbGUuY29tIn19.SzUGsxuWaZ8FnxwejsNOh-mU0GXIxRh6qn2JOz69RADOtewfOXvtTMGqQtnph4NijzQGOZoaUQWSy9-o5mJ6daZDmL2G_-75RMTjibCGw8bAfNlHh2-ftkufplNnjxLASXVnNjXkzOhb8qTCieNbsJW60yRTCf6NkmHqoCTZNfnvXAL3wZZ39ubGTDK4PR1gdF-kKGaEbHAX9yz2tGuFDdKaBAWHIdWGEbE_bfzQn2_W3Cozol2K1D7UrkaQDd7cqUiL8XXpkxI13ucW-SWGadCL5hae4OAQgK2SJ3F2PYO9jAg1XZCXNbUrWv-yb1SyZmaIiFPomfC-sYa2VitEYQ"
IMGUR_CLIENT_ID = "5dd7228264e1165" 

def log_message(message: str) -> None:
   """Print log message to console"""
   print(message)

def upload_image_to_soot(
   image_data: Union[str, bytes], 
   space_id: str, 
   is_base64: bool = True,
   verbose: bool = True
) -> Dict:
   """
   Upload an image to SOOT space
   
   Args:
       image_data: Image data, either base64 string or binary data
       space_id: Target SOOT space ID
       is_base64: Indicates if image_data is base64 encoded, if False assumes binary data
       verbose: Whether to print detailed logs
       
   Returns:
       Dictionary containing upload results:
       {
           "success": True/False,
           "message": "Description message",
           "image_url": "Uploaded Imgur URL",
           "soot_intent_id": "SOOT intent ID"
       }
   """
   result = {
       "success": False,
       "message": "",
       "image_url": None,
       "soot_intent_id": None
   }
   
   try:
       # Ensure image_data is in base64 format
       if not is_base64:
           if verbose:
               log_message("[🔄] Converting binary data to base64...")
           if isinstance(image_data, bytes):
               image_data = base64.b64encode(image_data).decode('utf-8')
           else:
               raise ValueError("When is_base64=False, image_data must be bytes")
       
       # 1. Upload to Imgur to get URL
       if verbose:
           log_message("[📤] Step 1: Uploading image to Imgur...")
       image_url = upload_to_imgur(image_data, verbose=verbose)
       if not image_url:
           result["message"] = "Failed to upload image to Imgur"
           return result
       
       result["image_url"] = image_url
       
       # 2. Upload to SOOT
       if verbose:
           log_message(f"[📤] Step 2: Uploading image to SOOT space: {space_id}...")
       
       # 2.1 Create upload intent
       intent_id = create_upload_intent(space_id, verbose=verbose)
       result["soot_intent_id"] = intent_id
       
       # 2.2 Upload from URL
       upload_image_from_url(intent_id, [image_url], verbose=verbose)
       
       # 2.3 Complete upload intent
       complete_upload_intent(intent_id, verbose=verbose)
       
       result["success"] = True
       result["message"] = "Image successfully uploaded to SOOT"
       
       if verbose:
           log_message("[🎉] Upload process completed successfully!")
       
       return result
       
   except Exception as e:
       error_message = str(e)
       if verbose:
           log_message(f"[❌] Upload process error: {error_message}")
           import traceback
           traceback.print_exc()
       
       result["message"] = f"Error: {error_message}"
       return result

def upload_to_imgur(image_data_base64: str, verbose: bool = True) -> Optional[str]:
   """Upload base64 encoded image to Imgur and return URL"""
   if not IMGUR_CLIENT_ID:
       raise ValueError("IMGUR_CLIENT_ID not provided")
   
   try:
       if verbose:
           log_message("[🔄] Uploading image to Imgur...")
           log_message(f"[📊] Base64 image length: {len(image_data_base64)} characters")
       
       # Imgur API endpoint
       url = "https://api.imgur.com/3/image"
       
       # Prepare headers and data
       headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}
       data = {"image": image_data_base64, "type": "base64"}
       
       # Send request
       response = requests.post(url, headers=headers, data=data)
       
       if verbose:
           log_message(f"[📡] Imgur API response status: {response.status_code}")
       
       # If error, print more information
       if response.status_code != 200:
           if verbose:
               log_message(f"[❌] Imgur API error: {response.text}")
           response.raise_for_status()
       
       # Parse response
       result = response.json()
       if not result["success"]:
           error_msg = result.get("data", {}).get("error", "Unknown error")
           if verbose:
               log_message(f"[❌] Imgur upload failed: {error_msg}")
           raise Exception(f"Imgur API error: {error_msg}")
       
       # Get image URL and delete hash
       image_url = result["data"]["link"]
       delete_hash = result["data"]["deletehash"]
       
       if verbose:
           log_message(f"[✅] Image uploaded to Imgur successfully!")
           log_message(f"[🔗] Image URL: {image_url}")
           log_message(f"[🗑️] Delete hash (for image removal): {delete_hash}")
       
       return image_url
       
   except Exception as e:
       if verbose:
           log_message(f"[❌] Imgur upload error: {e}")
       raise

def create_upload_intent(space_id: str, verbose: bool = True) -> str:
   """Create SOOT upload intent"""
   if verbose:
       log_message(f"[🔄] Creating upload intent for space '{space_id}'...")
   
   if not SOOT_ACCESS_TOKEN:
       raise ValueError("SOOT_ACCESS_TOKEN not provided")
   
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

   try:
       response = requests.post(SOOT_API, headers=headers, json=payload)
       
       if verbose:
           log_message(f"[📡] SOOT API response status: {response.status_code}")
       
       if response.status_code != 200:
           if verbose:
               log_message(f"[❌] SOOT API error: {response.text}")
           response.raise_for_status()
           
       result = response.json()
       if 'errors' in result:
           if verbose:
               log_message(f"[❌] GraphQL errors: {result['errors']}")
           raise Exception(f"GraphQL errors: {result['errors']}")

       intent = result['data']['createUploadIntent'].get('uploadIntent', {})
       intent_id = intent.get('id')
       if not intent_id:
           if verbose:
               log_message(f"[❌] Failed to extract uploadIntent ID: {result}")
           raise Exception(f"Failed to extract uploadIntent ID: {result}")

       if verbose:
           log_message(f"[🔑] Upload intent created: ID={intent_id}")
       return intent_id
   
   except Exception as e:
       if verbose:
           log_message(f"[❌] Error creating upload intent: {e}")
       raise

def upload_image_from_url(intent_id: str, image_urls: List[str], verbose: bool = True):
   """Upload image from URL to SOOT"""
   if verbose:
       log_message(f"[🔄] Uploading image from URL to SOOT...")
       log_message(f"[📊] Upload intent ID: {intent_id}")
       log_message(f"[📊] Image URL: {image_urls[0]}")
   
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

   try:
       response = requests.post(SOOT_API, headers=headers, json=payload)
       
       if verbose:
           log_message(f"[📡] SOOT API response status: {response.status_code}")
       
       if response.status_code != 200:
           if verbose:
               log_message(f"[❌] SOOT API error: {response.text}")
           response.raise_for_status()
           
       result = response.json()
       if 'errors' in result:
           if verbose:
               log_message(f"[❌] GraphQL errors: {result['errors']}")
           raise Exception(f"GraphQL errors: {result['errors']}")

       typename = result['data']['uploadFromUrl']['__typename']
       if typename != "UploadFromUrlResult":
           if verbose:
               log_message(f"[❌] Upload failed: {typename}")
           raise Exception(f"Upload failed: {typename}")

       if verbose:
           log_message(f"[✅] Upload request accepted; SOOT will fetch the image.")
   
   except Exception as e:
       if verbose:
           log_message(f"[❌] Error uploading image from URL: {e}")
       raise

def complete_upload_intent(intent_id: str, count: int = 1, verbose: bool = True):
   """Complete SOOT upload intent"""
   if verbose:
       log_message(f"[🔄] Completing upload intent '{intent_id}' with {count} file(s)...")
   
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

   try:
       response = requests.post(SOOT_API, headers=headers, json=payload)
       
       if verbose:
           log_message(f"[📡] SOOT API response status: {response.status_code}")
       
       if response.status_code != 200:
           if verbose:
               log_message(f"[❌] SOOT API error: {response.text}")
           response.raise_for_status()
           
       result = response.json()
       if 'errors' in result:
           if verbose:
               log_message(f"[❌] GraphQL errors: {result['errors']}")
           raise Exception(f"GraphQL errors: {result['errors']}")

       if verbose:
           log_message(f"[✅] Upload intent '{intent_id}' completed.")
   
   except Exception as e:
       if verbose:
           log_message(f"[❌] Error completing upload intent: {e}")
       raise