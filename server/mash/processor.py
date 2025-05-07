import requests
import os
import base64
import mimetypes
import threading
import json
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

BEARER_TOKEN = os.getenv("SOOT_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Fixed model names
GEMINI_MODEL_NAME = "gemini-1.5-flash"  # For text generation and tagging
GEMINI_IMAGE_MODEL_NAME = "gemini-2.0-flash-exp"  # For image generation

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
        
        # Handle if the response comes in a code block format
        if "```json" in tags_text:
            # Extract the JSON part from inside the code block
            tags_text = tags_text.split("```json")[1].split("```")[0].strip()
        elif "```" in tags_text:
            # Handle other code block formats without language specification
            tags_text = tags_text.split("```")[1].split("```")[0].strip()
            
        # Now try to parse the JSON
        if tags_text.startswith("["):
            try:
                tags = json.loads(tags_text)
                print(f"[🏷️] Tags parsed: {tags}")
                return tags
            except json.JSONDecodeError as e:
                print(f"[⚠️] JSON decode error: {e}")
                # Try to extract tags manually as fallback
                import re
                # Look for anything in quotes
                potential_tags = re.findall(r'"([^"]*)"', tags_text)
                if potential_tags:
                    print(f"[🏷️] Tags extracted manually: {potential_tags}")
                    return potential_tags
                return []
        else:
            print(f"[⚠️] Tag format unexpected: {tags_text}")
            return []

    except Exception as e:
        print(f"[💥] Tag generation failed for {meta.instanceId[:6]}: {e}")
        return []

def get_all_cached_descriptions() -> List[Dict]:
    with cache_lock:
        cleaned = []
        for record in description_cache.values():
            filtered = {k: v for k, v in record.items() if k != "imageBase64"}
            cleaned.append(filtered)
        return cleaned

def find_best_matching_image(prompt: str) -> Optional[Dict]:
    """
    Find the best matching image for a user prompt based on descriptions and tags.
    
    Args:
        prompt: User's prompt
        
    Returns:
        The best matching image record, or None if no matches
    """
    print(f"[🔍] Finding best match for prompt: {prompt}")
    
    with cache_lock:
        if not description_cache:
            print("[⚠️] No cached images available")
            return None
        
        cached_descriptions_copy = description_cache.copy()
    
    # Use text processing model
    matching_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    
    best_match = None
    highest_score = -1
    
    for instance_id, record in cached_descriptions_copy.items():
        # Extract description and tags
        description = record.get("description", "")
        tags = record.get("tags", [])
        
        # Create a context for matching
        context = f"Description: {description}\nTags: {', '.join(tags)}"
        
        try:
            # Ask Gemini to score the match between the prompt and the image
            response = matching_model.generate_content(
                [{"text": f"""
                Task: Rate how well an image matches a user prompt.
                
                Image context:
                {context}
                
                User prompt: 
                {prompt}
                
                On a scale of 0 to 10, how relevant is this image to the user's prompt?
                Return only a number between 0 and 10.
                """}]
            )
            
            # Extract the score
            score_text = response.text.strip()
            # Handle possible text format
            score_text = ''.join(char for char in score_text if char.isdigit() or char == '.')
            
            try:
                score = float(score_text)
                print(f"[📊] Image {instance_id[:6]} score: {score}")
                
                if score > highest_score:
                    highest_score = score
                    best_match = record
            except ValueError:
                print(f"[⚠️] Could not parse score: {score_text}")
                continue
                
        except Exception as e:
            print(f"[❌] Error scoring match for {instance_id[:6]}: {e}")
            continue
    
    if best_match:
        print(f"[✅] Best match found: {best_match['instanceId'][:6]} with score {highest_score}")
    else:
        print("[❌] No suitable match found")
        
    return best_match

def apply_operation_to_image(image_record: Dict, prompt: str) -> Dict:
    """
    Apply the user's prompt operation to the selected image
    
    Args:
        image_record: The selected image record
        prompt: User's prompt for operation
        
    Returns:
        Updated image record with results
    """
    print(f"[🔧] Applying operation to image: {image_record['instanceId'][:6]}")
    
    # Get image data
    image_base64 = image_record.get("imageBase64", "")
    if not image_base64:
        print("[⚠️] No image data available")
        return image_record
    
    try:
        # Decode image
        image_bytes = base64.b64decode(image_base64)
        metadata = image_record.get("metadata", {})
        mime_type = mimetypes.guess_type(metadata.get("filename", "") or "")[0] or "image/png"
        
        # Use our tested image generation model and parameters
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_IMAGE_MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
        
        # Correctly formatted payload with inlineData instead of inline_data
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": image_base64
                            }
                        },
                        {
                            "text": f"Based on this image, {prompt}"
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "topK": 32,
                "topP": 1,
                "response_modalities": ["TEXT", "IMAGE"],
                "maxOutputTokens": 2048
            }
        }
        
        # Send request
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, json=payload)
        
        # Check for errors
        if response.status_code != 200:
            print(f"[❌] API error: {response.status_code}")
            print(f"[❌] Error details: {response.text}")
            return {
                "originalInstanceId": image_record["instanceId"],
                "prompt": prompt,
                "error": f"API error: {response.status_code}"
            }
        
        # Parse response
        result_json = response.json()
        
        # Save full response for debugging
        with open(f"gemini_response_{image_record['instanceId'][:6]}.json", "w") as f:
            json.dump(result_json, f, indent=2)
        
        # Result to return
        result = {
            "originalInstanceId": image_record["instanceId"],
            "prompt": prompt,
            "result": {}
        }
        
        # Extract image data from response
        if 'candidates' in result_json and result_json['candidates']:
            for candidate in result_json['candidates']:
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        # Check for image data
                        if 'inlineData' in part and 'data' in part['inlineData']:
                            # Image data is Base64 encoded
                            result["result"]["imageBase64"] = part['inlineData']['data']
                            print("[✅] Generated new image successfully")
                        
                        # If there is text response
                        if 'text' in part:
                            result["result"]["description"] = part['text']
                            print(f"[📝] Generation description: {part['text'][:100]}...")
        
        return result
    
    except Exception as e:
        print(f"[❌] Error applying operation: {e}")
        import traceback
        traceback.print_exc()
        return {
            "originalInstanceId": image_record["instanceId"],
            "prompt": prompt,
            "error": str(e)
        }

def handle_user_prompt(prompt: str):
    """
    Handle user prompt by finding the best matching image and applying the operation
    
    Args:
        prompt: User's prompt
        
    Returns:
        Result of the operation
    """
    print(f"[🟡] Handling user prompt: {prompt}")
    
    # Find best matching image
    best_match = find_best_matching_image(prompt)
    
    if not best_match:
        return {"error": "No suitable image found for the prompt"}
    
    # Apply operation to image
    result = apply_operation_to_image(best_match, prompt)
    
    # Save the generated image to local file for inspection
    if "result" in result and "imageBase64" in result["result"]:
        try:
            # Decode the base64 image
            image_data = base64.b64decode(result["result"]["imageBase64"])
            
            # Generate a filename using the original image ID and the prompt
            original_id = best_match["instanceId"][:6]
            safe_prompt = "".join(x for x in prompt if x.isalnum() or x.isspace()).replace(" ", "_")[:30]
            filename = f"generated_{original_id}_{safe_prompt}.png"
            
            # Save the image
            with open(filename, "wb") as f:
                f.write(image_data)
            print(f"[💾] Saved generated image to {filename}")
            
            # Add the local filename to the result
            result["localFilename"] = filename
            
            # Add all the original image metadata to preserve context
            result["originalMetadata"] = best_match.get("metadata", {})
            result["originalDescription"] = best_match.get("description", "")
            result["originalTags"] = best_match.get("tags", [])
        except Exception as e:
            print(f"[❌] Error saving image: {e}")
    
    return result