import os
import requests
import json
import base64
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment variables
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable must be set")

def generate_image(prompt):
    """
    Generate an image using Gemini API
    
    Args:
        prompt: Text prompt describing what image to generate
        
    Returns:
        Generated image object if successful
    """
    print(f"Generating image: {prompt}")
    
    # Use the specialized image generation model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
    
    # Request body
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "topK": 32,
            "topP": 1,
            "response_modalities": ["TEXT", "IMAGE"],  # Correct parameter name
            "maxOutputTokens": 2048
        }
    }
    
    # Send request
    try:
        print("Sending request to Gemini API...")
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, json=payload)
        
        # Check for errors
        if response.status_code != 200:
            print(f"API error: {response.status_code}")
            print(f"Error details: {response.text}")
            return None
            
        # Parse response
        result = response.json()
        print("Response received, processing...")
        
        # Save complete response for debugging
        with open("gemini_image_response.json", "w") as f:
            json.dump(result, f, indent=2)
        
        # Extract image data from response
        if 'candidates' in result and result['candidates']:
            for candidate in result['candidates']:
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        # Check if there's image data
                        if 'inlineData' in part and 'data' in part['inlineData']:
                            # Image data is Base64 encoded
                            image_data = part['inlineData']['data']
                            image_bytes = base64.b64decode(image_data)
                            
                            # Convert image data to PIL Image object
                            image = Image.open(BytesIO(image_bytes))
                            return image
                            
                        # If there's text response, print it
                        if 'text' in part:
                            print("API returned text response:")
                            print(part['text'][:500] + "..." if len(part['text']) > 500 else part['text'])
        
        print("No image data found in response")
        return None
        
    except Exception as e:
        print(f"Error generating image: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    # Prompt
    prompt = "A 3D rendered pig with wings and a top hat flying over a futuristic sci-fi city filled with green plants"
    
    # Generate image
    image = generate_image(prompt)
    
    # Save and display image (if successful)
    if image:
        print("Image generated successfully!")
        image.save('gemini_generated_image.png')
        print("Image saved as 'gemini_generated_image.png'")
        image.show()
    else:
        print("Could not generate image")
        print("\nTry other parameters:")
        print("1. Try using gemini-2.0-flash-exp-image-generation or gemini-2.0-flash-preview-image-generation model")
        print("2. Check response format, view gemini_image_response.json file")
        print("3. Confirm your account has permission to use image generation models")

if __name__ == "__main__":
    main()