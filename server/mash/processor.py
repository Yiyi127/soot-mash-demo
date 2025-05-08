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
            
            frontend_payloads.append({
                "metadata": meta.dict(),
                "imageBase64": image_base64
            })

            print(f"[📤] Payload ready for frontend: {meta.filename or meta.instanceId[:6]}")

            # Start async processing
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
            # Improved prompt for more consistent scoring
            response = matching_model.generate_content(
                [{"text": f"""
                Task: Score how relevant an image is to a specific prompt.
                
                Image information:
                {context}
                
                User prompt: 
                {prompt}
                
                Using only the information provided about the image (without seeing it), assign a relevance score 
                from 0 to 10, where 0 means completely irrelevant and 10 means perfect match.
                
                Return only a number between 0 and 10.
                """}]
            )
            
            # Extract the score
            score_text = response.text.strip()
            # Handle possible text format - extract just the number
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

def find_second_best_matching_image(prompt: str, exclude_id: str) -> Optional[Dict]:
    """
    Find the second best matching image for a prompt, excluding the specified ID
    
    Args:
        prompt: User's prompt
        exclude_id: Instance ID to exclude
        
    Returns:
        The second best matching image, or None if no matches
    """
    print(f"[🔍] Finding second best match for prompt: {prompt}, excluding {exclude_id[:6]}")
    
    with cache_lock:
        if not description_cache:
            print("[⚠️] No cached images available")
            return None
        
        cached_descriptions_copy = {k: v for k, v in description_cache.items() if k != exclude_id}
    
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
            # Improved prompt for more consistent scoring
            response = matching_model.generate_content(
                [{"text": f"""
                Task: Score how relevant an image is to a specific prompt.
                
                Image information:
                {context}
                
                User prompt: 
                {prompt}
                
                Using only the information provided about the image (without seeing it), assign a relevance score 
                from 0 to 10, where 0 means completely irrelevant and 10 means perfect match.
                
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
        print(f"[✅] Second best match found: {best_match['instanceId'][:6]} with score {highest_score}")
    else:
        print("[❌] No suitable second match found")
        
    return best_match

def parse_user_command(command: str) -> dict:
    """
    Parse user command to identify command type and parameters
    
    Args:
        command: User's input command
        
    Returns:
        Dictionary with command information
    """
    result = {
        "command_type": "unknown",
        "original_command": command,
        "parameters": "",
        "mash_info": None
    }
    
    # Check for empty command
    if not command or not command.strip():
        return result
    
    command = command.strip()
    
    # Parse mash command - checking for "mash:" exactly
    if command.lower() == "mash:" or command.lower().startswith("mash:"):
        result["command_type"] = "mash"
        result["parameters"] = command[5:].strip()
        
        # Parse mash details if provided
        result["mash_info"] = parse_mash_details(result["parameters"])
    
    # If no known prefix, treat as a general prompt
    else:
        result["command_type"] = "prompt"
        result["parameters"] = command
    
    print(f"[🔍] Parsed command: {result['command_type']} with parameters: {result['parameters']}")
    return result

def parse_mash_details(prompt: str) -> Dict:
    """
    Parse a mash command parameters to extract feature filters and source references
    
    Args:
        prompt: User's mash parameters (e.g., "style from:1 content from:2")
        
    Returns:
        Dictionary with parsed command information
    """
    result = {
        "features": {},
        "sources": {},
        "is_empty": prompt.strip() == ""
    }
    
    print(f"[🔍] Checking if mash command is empty: '{prompt}' -> {result['is_empty']}")
    
    # If empty prompt, this is a "mash all" command
    if result["is_empty"]:
        return result
    
    # Extract feature filters and their sources
    current_feature = None
    
    for part in prompt.split():
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

def handle_mash_command(parsed_command: Dict) -> Dict:
    """
    Handle mash command by combining images according to specifications
    
    Args:
        parsed_command: Parsed command information
        
    Returns:
        Result of the operation
    """
    print(f"[🔀] Processing mash command: {parsed_command}")
    
    # Check if this is an empty mash command (mash:)
    mash_info = parsed_command.get("mash_info", {})
    parameters = parsed_command.get("parameters", "")
    
    # Debug output to check the values
    print(f"[🔍] Mash parameters: '{parameters}'")
    print(f"[🔍] Is empty mash command: {mash_info.get('is_empty', False)}")
    
    # If this is an empty mash command (mash:), combine all images in pairs
    if mash_info and mash_info.get("is_empty", False):
        print(f"[✅] Detected empty mash command, routing to handle_mash_all_images()")
        return handle_mash_all_images()
    
    # Collect all source images for specified features
    source_images = {}
    
    # Check if we have valid sources
    if not mash_info or not mash_info.get("sources"):
        # If no explicit sources, find best matching images for each feature
        return find_and_mash_best_matches(parameters)
    
    # Get source images for each feature
    for feature, source_index in mash_info.get("sources", {}).items():
        source_image = get_image_by_index(source_index)
        if source_image:
            source_images[feature] = source_image
            print(f"[🔍] Found source for {feature}: image #{source_index} ({source_image['instanceId'][:6]})")
        else:
            print(f"[⚠️] Source not found for {feature}: image #{source_index}")
    
    # Check if we have enough sources
    if not source_images:
        return {"error": "No valid source images found"}
    
    if len(source_images) < len(mash_info.get("sources", {})):
        return {"error": "One or more source images not found"}
    
    # Determine the base image (either specified as "base" or the first source)
    base_feature = next((f for f in mash_info.get("sources", {}).keys() if f == "base"), None)
    if not base_feature:
        # If no explicit base, use the first source
        base_feature = next(iter(mash_info.get("sources", {}).keys()))
    
    base_image = source_images[base_feature]
    
    # Apply the mash operation
    result = apply_operation_to_image(base_image, parsed_command["original_command"], source_images)
    
    return result


def handle_mash_all_images() -> Dict:
    """
    Handle 'mash:' command (without parameters) by combining all images in pairs.
    Generates n*n-n combinations (excluding self-combinations).
    
    Returns:
        Result with all generated combinations
    """
    print("[🔄] Processing mash all images command")
    
    with cache_lock:
        all_images = list(description_cache.values())
        
    if len(all_images) < 2:
        return {"error": "Need at least 2 images to perform mash all operation"}
    
    total_images = len(all_images)
    # n*n-n combinations (excluding self with self)
    max_combinations = total_images * total_images - total_images
    
    print(f"[🔀] Starting mash of all {total_images} images ({max_combinations} combinations)")
    
    # Prepare array to store all combinations
    all_combinations = []
    
    # Generate combinations by applying each image's style to every other image
    for i, style_image in enumerate(all_images):
        for j, content_image in enumerate(all_images):
            # Skip self-combinations
            if i == j:
                continue
                
            # Create ID for this combination
            combo_id = f"style{i+1}_content{j+1}"
            print(f"[🔀] Processing combination {combo_id}")
            
            # Set up the source images for this combination
            source_images = {
                "style": style_image,
                "content": content_image
            }
            
            # Create a descriptive prompt
            style_desc = style_image.get("description", f"image {i+1}")
            content_desc = content_image.get("description", f"image {j+1}")
            mash_prompt = f"Apply style from image {i+1} to content of image {j+1}"
            
            try:
                # Apply the mash operation
                result = apply_operation_to_image(
                    content_image,  # Use content as base
                    mash_prompt,
                    source_images
                )
                
                # Add metadata for tracking
                result["styleImageIndex"] = i + 1
                result["contentImageIndex"] = j + 1
                result["styleImageId"] = style_image["instanceId"]
                result["contentImageId"] = content_image["instanceId"]
                result["combinationId"] = combo_id
                
                # Add to results
                all_combinations.append(result)
                
                print(f"[✅] Completed combination {len(all_combinations)}/{max_combinations}")
                
            except Exception as e:
                print(f"[❌] Error processing combination {i+1}×{j+1}: {e}")
                error_result = {
                    "styleImageIndex": i + 1,
                    "contentImageIndex": j + 1,
                    "error": f"Failed to process: {str(e)}"
                }
                all_combinations.append(error_result)
    
    # Final logging
    print(f"[🎉] Successfully generated {len(all_combinations)} image combinations")
    
    # Return the results
    return {
        "command": "mash:",
        "total_images": total_images,
        "expected_combinations": max_combinations,
        "actual_combinations": len(all_combinations),
        "combinations": all_combinations
    }

def find_and_mash_best_matches(prompt: str) -> Dict:
    """
    Find two best matching images for the given prompt and mash them together
    
    Args:
        prompt: User's prompt
        
    Returns:
        Result of the mash operation
    """
    print(f"[🔍] Finding best matches for mash prompt: {prompt}")
    
    # Find the best matching image for style
    style_match = find_best_matching_image("style " + prompt)
    
    # Find the best matching image for content
    content_match = find_best_matching_image("content " + prompt)
    
    if not style_match or not content_match:
        return {"error": "Could not find suitable images to match the prompt"}
    
    if style_match["instanceId"] == content_match["instanceId"]:
        # Try to find a different content match
        second_match = find_second_best_matching_image("content " + prompt, exclude_id=style_match["instanceId"])
        if second_match:
            content_match = second_match
    
    # Set up the source images
    source_images = {
        "style": style_match,
        "content": content_match
    }
    
    # Create enhanced mash prompt
    style_desc = style_match.get("description", "unknown style")
    content_desc = content_match.get("description", "unknown content")
    mash_prompt = f"Apply the style of '{style_desc}' to the content of '{content_desc}'"
    
    # Apply the mash operation
    result = apply_operation_to_image(
        content_match,  # Use content as base
        mash_prompt,
        source_images
    )
    
    # Add metadata about the matches
    result["styleImageId"] = style_match["instanceId"]
    result["contentImageId"] = content_match["instanceId"]
    result["styleImageDescription"] = style_desc
    result["contentImageDescription"] = content_desc
    
    return result


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
        
        # Use the provided prompt directly - don't modify it
        enhanced_prompt = prompt
        
        # Skip the "Create a new image that combines" prefix for mash commands
        # Just use the original prompt
        
        print(f"[✏️] Using prompt: {enhanced_prompt}")
        
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
            "originalPrompt": prompt,
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
    Handle user prompt by parsing the command type and routing to appropriate handler
    
    Args:
        prompt: User's prompt
        
    Returns:
        Result of the operation
    """
    print(f"[🟡] Handling user prompt: {prompt}")
    
    # Parse the user command
    parsed_command = parse_user_command(prompt)
    
    # Route to the appropriate handler based on command type
    if parsed_command["command_type"] == "mash":
        return handle_mash_command(parsed_command)
    
    # For standard prompts or unknown commands
    else:
        # Find the best matching image
        best_match = find_best_matching_image(parsed_command["parameters"])
        
        if not best_match:
            return {"error": "No suitable image found for the prompt"}
        
        # Apply operation to image
        result = apply_operation_to_image(best_match, parsed_command["parameters"])
        
        return result

