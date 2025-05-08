import requests
import os
import base64
import mimetypes
import threading
import json
import re
from typing import List, Dict, Tuple, Optional, Union
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

            # Save the image locally so you can see it
            local_filename = f"original_{meta.instanceId[:6]}.png"
            with open(local_filename, "wb") as f:
                f.write(image_bytes)
            print(f"[💾] Saved original image to {local_filename}")

            frontend_payloads.append({
                "metadata": meta.dict(),
                "imageBase64": image_base64,
                "localFilename": local_filename  # Add local filename to the payload
            })

            print(f"[📤] Payload ready for frontend: {meta.filename or meta.instanceId[:6]}")

            threading.Thread(
                target=_generate_and_cache_description,
                args=(meta, image_base64, local_filename)
            ).start()

        except Exception as e:
            print(f"[❌] Failed to process {meta.filename or meta.instanceId[:6]}: {e}")
            continue

    print(f"[✅] Total payloads returned: {len(frontend_payloads)}")
    return frontend_payloads

def _generate_and_cache_description(meta: Metadata, image_base64: str, local_filename: str):
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
            "rawResponse": raw_response,
            "localFilename": local_filename  # Store local filename in record
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
            {"text": "List 5 to 8 concise, lowercase tags that best describe the image content. Include tags for style, background, foreground, composition, and lighting. Return only a JSON array."}
        ])

        tags_text = response.text.strip()
        
        # Handle if the response comes in a code block format
        if "```json" in tags_text:
            tags_text = tags_text.split("```json")[1].split("```")[0].strip()
        elif "```" in tags_text:
            tags_text = tags_text.split("```")[1].split("```")[0].strip()
            
        # Parse JSON tags
        if tags_text.startswith("["):
            try:
                tags = json.loads(tags_text)
                print(f"[🏷️] Tags parsed: {tags}")
                return tags
            except json.JSONDecodeError as e:
                print(f"[⚠️] JSON decode error: {e}")
                # Extract tags manually as fallback
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

def parse_mash_command(prompt: str) -> Dict:
    """
    Parse a mash command to extract feature filters and source references
    
    Args:
        prompt: User's mash command (e.g., "mash style from:1 content from:2")
        
    Returns:
        Dictionary with parsed command information
    """
    result = {
        "is_mash": False,
        "original_prompt": prompt,
        "features": {},
        "sources": {},
    }
    
    # Check if it's a mash command
    if not prompt.lower().startswith("mash "):
        return result
    
    # Mark as mash command
    result["is_mash"] = True
    
    # Extract the mash instruction part (everything after "mash ")
    mash_instruction = prompt[5:].strip()
    
    # Extract feature filters and their sources
    current_feature = None
    
    for part in mash_instruction.split():
        if "from:" in part:
            # This is a source reference (e.g., "from:1")
            source_index_match = re.search(r'from:(\d+)', part)
            if source_index_match and current_feature:
                try:
                    source_index = int(source_index_match.group(1))
                    result["sources"][current_feature] = source_index
                except ValueError:
                    pass
        else:
            # This is a feature (e.g., "style", "background", etc.)
            current_feature = part.lower()
            result["features"][current_feature] = True
    
    return result

def get_image_by_index(index: int) -> Optional[Dict]:
    """
    Get an image from the cache by its index (1-based)
    
    Args:
        index: 1-based index of the image in the cache
        
    Returns:
        The image record or None if not found
    """
    with cache_lock:
        all_images = list(description_cache.values())
        # Convert 1-based index to 0-based index
        idx = index - 1
        if 0 <= idx < len(all_images):
            return all_images[idx]
    return None

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

def apply_operation_to_image(image_record: Dict, prompt: str, source_images: Dict = None) -> Dict:
    """
    Apply the user's prompt operation to the selected image
    
    Args:
        image_record: The selected image record
        prompt: User's prompt for operation
        source_images: Optional dict of source images for mash operations
        
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
        
        # Create a more specific prompt for Gemini based on the operation
        enhanced_prompt = prompt
        
        # If this is a mash operation with source images
        if source_images:
            enhanced_prompt = "Create a new image that combines: "
            
            # Add details for each source image and its feature
            for feature, source_image in source_images.items():
                source_desc = source_image.get("description", "")
                if feature == "style":
                    enhanced_prompt += f"the visual style from '{source_desc}', "
                elif feature == "content":
                    enhanced_prompt += f"the content and subjects from '{source_desc}', "
                elif feature == "background":
                    enhanced_prompt += f"the background elements from '{source_desc}', "
                elif feature == "foreground":
                    enhanced_prompt += f"the foreground elements from '{source_desc}', "
                elif feature == "composition":
                    enhanced_prompt += f"the composition from '{source_desc}', "
                elif feature == "lighting":
                    enhanced_prompt += f"the lighting qualities from '{source_desc}', "
                else:
                    enhanced_prompt += f"the {feature} from '{source_desc}', "
            
            # Remove trailing comma and space
            enhanced_prompt = enhanced_prompt.rstrip(", ")
        
        print(f"[✏️] Enhanced prompt: {enhanced_prompt}")
        
        # Use image generation model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_IMAGE_MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
        
        # Prepare parts for the request
        parts = []
        
        # First add the main image
        parts.append({
            "inlineData": {
                "mimeType": mime_type,
                "data": image_base64
            }
        })
        
        # Add source images for mash operations
        if source_images:
            for feature, source_image in source_images.items():
                if feature != "base" and "imageBase64" in source_image:
                    source_mime_type = mimetypes.guess_type(
                        source_image.get("metadata", {}).get("filename", "") or ""
                    )[0] or "image/png"
                    
                    parts.append({
                        "inlineData": {
                            "mimeType": source_mime_type,
                            "data": source_image["imageBase64"]
                        }
                    })
        
        # Add the text prompt at the end
        parts.append({
            "text": enhanced_prompt
        })
        
        # Format payload
        payload = {
            "contents": [
                {
                    "parts": parts
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
            "enhancedPrompt": enhanced_prompt,
            "result": {}
        }
        
        # If this was a mash command, add source information
        if source_images:
            result["mashSources"] = {}
            for feature, source_image in source_images.items():
                result["mashSources"][feature] = {
                    "instanceId": source_image["instanceId"],
                    "description": source_image.get("description", "")
                }
        
        # Extract image data from response
        if 'candidates' in result_json and result_json['candidates']:
            for candidate in result_json['candidates']:
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        # Check for image data
                        if 'inlineData' in part and 'data' in part['inlineData']:
                            # Image data is Base64 encoded
                            generated_image_base64 = part['inlineData']['data']
                            result["result"]["imageBase64"] = generated_image_base64
                            print("[✅] Generated new image successfully")
                            
                            # Save the generated image to local file for viewing
                            try:
                                image_data = base64.b64decode(generated_image_base64)
                                
                                # Generate a filename using the original image ID and the prompt
                                original_id = image_record["instanceId"][:6]
                                safe_prompt = "".join(c for c in prompt[:20] if c.isalnum() or c.isspace()).replace(" ", "_")
                                filename = f"generated_{original_id}_{safe_prompt}.png"
                                
                                # Save the image
                                with open(filename, "wb") as f:
                                    f.write(image_data)
                                print(f"[💾] Saved generated image to {filename}")
                                
                                # Add the local filename to the result
                                result["localFilename"] = filename
                                
                                # Create a simple HTML file to view the image
                                html_filename = f"view_{original_id}_{safe_prompt}.html"
                                with open(html_filename, "w") as f:
                                    f.write(f"""
                                    <!DOCTYPE html>
                                    <html>
                                    <head>
                                        <title>Generated Image</title>
                                        <style>
                                            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                                            h1 {{ color: #333; }}
                                            .image-container {{ margin: 20px 0; }}
                                            img {{ max-width: 100%; border: 1px solid #ddd; }}
                                            .details {{ background: #f9f9f9; padding: 15px; border-radius: 5px; }}
                                        </style>
                                    </head>
                                    <body>
                                        <h1>Generated Image</h1>
                                        <div class="details">
                                            <p><strong>Prompt:</strong> {prompt}</p>
                                            <p><strong>Enhanced Prompt:</strong> {enhanced_prompt}</p>
                                        </div>
                                        <div class="image-container">
                                            <h2>Generated Image</h2>
                                            <img src="{filename}" alt="Generated image">
                                        </div>
                                        <div class="image-container">
                                            <h2>Original Image</h2>
                                            <img src="{image_record.get('localFilename', '')}" alt="Original image">
                                        </div>
                                    </body>
                                    </html>
                                    """)
                                print(f"[🌐] Created HTML viewer: {html_filename}")
                                result["htmlViewer"] = html_filename
                                
                            except Exception as e:
                                print(f"[❌] Error saving image: {e}")
                        
                        # If there is text response
                        if 'text' in part:
                            result["result"]["description"] = part['text']
                            print(f"[📝] Generation description: {part['text'][:100]}...")
        
        # Add all the original image metadata to preserve context
        result["originalMetadata"] = image_record.get("metadata", {})
        result["originalDescription"] = image_record.get("description", "")
        result["originalTags"] = image_record.get("tags", [])
        
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
    
    # Parse mash command if present
    parsed_command = parse_mash_command(prompt)
    
    # If this is a mash command
    if parsed_command["is_mash"]:
        print(f"[🔀] Processing mash command: {parsed_command}")
        
        # Collect all source images
        source_images = {}
        
        # Check if we have valid sources
        if not parsed_command["sources"]:
            return {"error": "Invalid mash command. Please specify sources with 'from:X' syntax"}
        
        # Get source images for each feature
        for feature, source_index in parsed_command["sources"].items():
            source_image = get_image_by_index(source_index)
            if source_image:
                source_images[feature] = source_image
                print(f"[🔍] Found source for {feature}: image #{source_index} ({source_image['instanceId'][:6]})")
            else:
                print(f"[⚠️] Source not found for {feature}: image #{source_index}")
        
        # Check if we have enough sources
        if len(source_images) < len(parsed_command["sources"]):
            return {"error": "One or more source images not found"}
        
        # Determine the base image (either specified as "base" or the first source)
        base_feature = next((f for f in parsed_command["sources"].keys() if f == "base"), None)
        if not base_feature:
            # If no explicit base, use the first source
            base_feature = next(iter(parsed_command["sources"].keys()))
        
        base_image = source_images[base_feature]
        
        # Apply the mash operation
        result = apply_operation_to_image(base_image, parsed_command["original_prompt"], source_images)
        
        return result
    
    # For standard prompts
    best_match = find_best_matching_image(prompt)
    
    if not best_match:
        return {"error": "No suitable image found for the prompt"}
    
    # Apply operation to image
    result = apply_operation_to_image(best_match, prompt)
    
    return result

# Example usage:
if __name__ == "__main__":
    # Example 1: Process a simple prompt
    result = handle_user_prompt("a futuristic cityscape at night")
    print(json.dumps(result, indent=2))
    
    # Example 2: Process a mash command (after loading some images)
    # result = handle_user_prompt("mash style from:1 content from:2")
    # print(json.dumps(result, indent=2))