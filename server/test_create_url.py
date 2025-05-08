import requests
import os
import base64
import mimetypes
import json
import time
from typing import List, Dict, Optional
import google.generativeai as genai

# 配置 - 根据你的环境调整这些变量
SOOT_API = "https://api.soot.com/graphql"  
SOOT_ACCESS_TOKEN ="eyJhbGciOiJSUzI1NiIsImtpZCI6IjU5MWYxNWRlZTg0OTUzNjZjOTgyZTA1MTMzYmNhOGYyNDg5ZWFjNzIiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiWm9leSBMaXUiLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jTDR6U1NIejRlQ0tZUElJMWJwMU5GMHp6cHdoZ2ZPcVhQSUxMVUVMZE1zZklKN3JRPXM5Ni1jIiwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL3Nvb3QtOTBkNTEiLCJhdWQiOiJzb290LTkwZDUxIiwiYXV0aF90aW1lIjoxNzQ2NTk4OTYxLCJ1c2VyX2lkIjoiMkxnU2Nld3Q2NGg1VWZneG5UcG9mZVJSMzU4MiIsInN1YiI6IjJMZ1NjZXd0NjRoNVVmZ3huVHBvZmVSUjM1ODIiLCJpYXQiOjE3NDY2OTEwMDgsImV4cCI6MTc0NjY5NDYwOCwiZW1haWwiOiJ4LXpvZXlAc29vdC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJnb29nbGUuY29tIjpbIjExNzY3MTI2MzcxNTQzMzcxMDY5MyJdLCJlbWFpbCI6WyJ4LXpvZXlAc29vdC5jb20iXX0sInNpZ25faW5fcHJvdmlkZXIiOiJnb29nbGUuY29tIn19.aK4t9bYfMuQgNPa3OT31xYD0Pd8dx1V7VGpXJrnCNMZeGVKHHtpXWv0Nl7xCcMrR9bSvUkUUNszvZFW0HxRLky4aEq-jfrHJQGK-0XEKHjrL2lSJdRp7HNsaB_oYfHwbhLxT1gOgntDUvg2cy78zlle7OeWGItptJF4ivwbNALYNVtxib2uvdcUJbjfDco03_p0tgy-SIEAZBhRAW60dhFLZSmidwclgYwLReZPXs0FXorwT8uXUT27V47b951WivyuMwMNd6oOWaLq1IIqjTeWEab3AbTZGAwxwlDGrl6H1lBY_gOukVoG-9Sli4Ladg8fAtdncq73Lv7gbdXotVA"
IMGUR_CLIENT_ID = "5dd7228264e1165" # 从环境变量获取，或者直接设置
GEMINI_API_KEY = "AIzaSyCznPFEfZDUkjWdI0bbMfOpPWxzObgoxsE" # 从环境变量获取，或者直接设置
SPACE_ID = "bae1c7d4-f130-450b-8c3e-a359caa885a0"  # 你的SOOT space ID

# 使用与你原始代码相同的Gemini模型
GEMINI_MODEL_NAME = "gemini-1.5-flash"  # 文本生成
GEMINI_IMAGE_MODEL_NAME = "gemini-2.0-flash-exp"  # 图像生成

# 初始化Gemini
def setup_gemini():
    """初始化Gemini API"""
    print("[🔧] Setting up Gemini API...")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    genai.configure(api_key=GEMINI_API_KEY)
    print("[✅] Gemini API configured successfully")
    return genai.GenerativeModel(GEMINI_MODEL_NAME)

# 使用Gemini生成图像
def generate_image_with_gemini(prompt: str) -> Optional[str]:
    """
    使用Gemini生成图像
    
    Args:
        prompt: 图像生成提示
        
    Returns:
        Base64编码的图像数据，失败时返回None
    """
    print(f"[🎨] Generating image with Gemini...")
    print(f"[📝] Prompt: {prompt}")
    
    try:
        # 构建API URL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_IMAGE_MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
        
        # 构建payload
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
                "response_modalities": ["TEXT", "IMAGE"],
                "maxOutputTokens": 2048
            }
        }
        
        # 发送请求
        headers = {
            "Content-Type": "application/json"
        }
        print("[🔄] Sending request to Gemini API...")
        response = requests.post(url, headers=headers, json=payload)
        
        # 检查响应状态
        print(f"[📡] Gemini API response status: {response.status_code}")
        
        # 如果出错，打印更多信息
        if response.status_code != 200:
            print(f"[❌] Gemini API error: {response.text}")
            response.raise_for_status()
        
        # 解析响应
        result_json = response.json()
        
        # 调试输出
        print("[🔍] Checking response for image data...")
        
        # 提取图像数据
        generated_image_base64 = None
        
        if 'candidates' in result_json and result_json['candidates']:
            for candidate in result_json['candidates']:
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        # 检查图像数据
                        if 'inlineData' in part and 'data' in part['inlineData']:
                            # 图像数据为Base64编码
                            generated_image_base64 = part['inlineData']['data']
                            print("[✅] Successfully extracted image data from Gemini response")
                            # 可选：保存到本地文件以便检查
                            with open("gemini_generated_image.txt", "w") as f:
                                f.write(generated_image_base64)
                            print("[💾] Saved base64 image data to gemini_generated_image.txt")
                            break
                    
                    # 如果找到图像数据，退出循环
                    if generated_image_base64:
                        break
        
        if not generated_image_base64:
            print("[❌] No image data found in Gemini response")
            print(f"[📊] Response structure: {json.dumps(result_json, indent=2)}")
            return None
        
        return generated_image_base64
        
    except Exception as e:
        print(f"[❌] Gemini image generation error: {e}")
        import traceback
        traceback.print_exc()
        return None

# Imgur上传函数
def upload_to_imgur(image_data_base64: str) -> Optional[str]:
    """
    上传base64编码的图片到Imgur并返回URL
    
    Args:
        image_data_base64: Base64编码的图片数据（不包含'data:image/png;base64,'前缀）
        
    Returns:
        图片URL，失败时返回None
    """
    if not IMGUR_CLIENT_ID:
        raise ValueError("IMGUR_CLIENT_ID environment variable not set")
    
    try:
        print("[🔄] Uploading image to Imgur...")
        print(f"[📊] Base64 image length: {len(image_data_base64)} characters")
        
        # Imgur API端点
        url = "https://api.imgur.com/3/image"
        
        # 准备请求头和数据
        headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}
        data = {"image": image_data_base64, "type": "base64"}
        
        # 发送请求
        response = requests.post(url, headers=headers, data=data)
        
        # 检查响应状态
        print(f"[📡] Imgur API response status: {response.status_code}")
        
        # 如果出错，打印更多信息
        if response.status_code != 200:
            print(f"[❌] Imgur API error: {response.text}")
            response.raise_for_status()
        
        # 解析响应
        result = response.json()
        if not result["success"]:
            error_msg = result.get("data", {}).get("error", "Unknown error")
            print(f"[❌] Imgur upload failed: {error_msg}")
            raise Exception(f"Imgur API error: {error_msg}")
        
        # 获取图片URL和删除哈希
        image_url = result["data"]["link"]
        delete_hash = result["data"]["deletehash"]
        
        print(f"[✅] Image uploaded to Imgur successfully!")
        print(f"[🔗] Image URL: {image_url}")
        print(f"[🗑️] Delete hash (save this to remove the image later): {delete_hash}")
        
        return image_url
        
    except Exception as e:
        print(f"[❌] Imgur upload error: {e}")
        import traceback
        traceback.print_exc()
        return None

# SOOT上传函数 - 1. 创建上传意图
def create_upload_intent(space_id: str) -> str:
    """创建SOOT上传意图"""
    print(f"[🔄] Creating upload intent for space '{space_id}'...")
    
    if not SOOT_ACCESS_TOKEN:
        raise ValueError("SOOT_ACCESS_TOKEN environment variable not set")
    
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
        
        # 打印响应状态
        print(f"[📡] SOOT API response status: {response.status_code}")
        
        # 如果出错，打印更多信息
        if response.status_code != 200:
            print(f"[❌] SOOT API error: {response.text}")
            response.raise_for_status()
            
        result = response.json()
        if 'errors' in result:
            print(f"[❌] GraphQL errors: {result['errors']}")
            raise Exception(f"GraphQL errors: {result['errors']}")

        intent = result['data']['createUploadIntent'].get('uploadIntent', {})
        intent_id = intent.get('id')
        if not intent_id:
            print(f"[❌] Failed to extract uploadIntent ID: {result}")
            raise Exception(f"Failed to extract uploadIntent ID: {result}")

        print(f"[🔑] Upload intent created: ID={intent_id}")
        return intent_id
    
    except Exception as e:
        print(f"[❌] Error creating upload intent: {e}")
        raise

# SOOT上传函数 - 2. 从URL上传
def upload_image_from_url(intent_id: str, image_urls: List[str]):
    """从URL上传图片到SOOT"""
    print(f"[🔄] Uploading image from URL to SOOT...")
    print(f"[📊] Upload intent ID: {intent_id}")
    print(f"[📊] Image URL: {image_urls[0]}")
    
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
        
        # 打印响应状态
        print(f"[📡] SOOT API response status: {response.status_code}")
        
        # 如果出错，打印更多信息
        if response.status_code != 200:
            print(f"[❌] SOOT API error: {response.text}")
            response.raise_for_status()
            
        result = response.json()
        if 'errors' in result:
            print(f"[❌] GraphQL errors: {result['errors']}")
            raise Exception(f"GraphQL errors: {result['errors']}")

        typename = result['data']['uploadFromUrl']['__typename']
        if typename != "UploadFromUrlResult":
            print(f"[❌] Upload failed: {typename}")
            raise Exception(f"Upload failed: {typename}")

        print(f"[✅] Upload request accepted; SOOT will fetch the image.")
    
    except Exception as e:
        print(f"[❌] Error uploading image from URL: {e}")
        raise

# SOOT上传函数 - 3. 完成上传意图
def complete_upload_intent(intent_id: str, count: int = 1):
    """完成SOOT上传意图"""
    print(f"[🔄] Completing upload intent '{intent_id}' with {count} file(s)...")
    
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
        
        # 打印响应状态
        print(f"[📡] SOOT API response status: {response.status_code}")
        
        # 如果出错，打印更多信息
        if response.status_code != 200:
            print(f"[❌] SOOT API error: {response.text}")
            response.raise_for_status()
            
        result = response.json()
        if 'errors' in result:
            print(f"[❌] GraphQL errors: {result['errors']}")
            raise Exception(f"GraphQL errors: {result['errors']}")

        print(f"[✅] Upload intent '{intent_id}' completed.")
    
    except Exception as e:
        print(f"[❌] Error completing upload intent: {e}")
        raise

# 主函数 - 使用Gemini生成图像，上传到Imgur，再上传到SOOT
def main():
    """主函数"""
    print("[🏁] Starting end-to-end test: Gemini -> Imgur -> SOOT")
    
    # 检查环境变量
    if not SOOT_ACCESS_TOKEN:
        print("[❌] SOOT_ACCESS_TOKEN environment variable not set")
        return
    
    if not IMGUR_CLIENT_ID:
        print("[❌] IMGUR_CLIENT_ID environment variable not set")
        return
    
    if not GEMINI_API_KEY:
        print("[❌] GEMINI_API_KEY environment variable not set")
        return
    
    try:
        # 1. 初始化Gemini
        setup_gemini()
        
        # 2. 使用Gemini生成图像
        prompt = "A beautiful landscape with mountains, a lake, and sunset"
        print(f"[🎨] Generating image with prompt: '{prompt}'")
        generated_image_base64 = generate_image_with_gemini(prompt)
        
        if not generated_image_base64:
            print("[❌] Failed to generate image with Gemini")
            return
        
        # 3. 上传生成的图像到Imgur
        print("[🔄] Uploading generated image to Imgur...")
        image_url = upload_to_imgur(generated_image_base64)
        
        if not image_url:
            print("[❌] Failed to upload image to Imgur")
            return
        
        # 4. 上传到SOOT
        print("[🔄] Uploading image to SOOT...")
        
        # 4.1 创建上传意图
        intent_id = create_upload_intent(SPACE_ID)
        
        # 4.2 从URL上传
        upload_image_from_url(intent_id, [image_url])
        
        # 4.3 完成上传意图
        complete_upload_intent(intent_id)
        
        print("[🎉] End-to-end test completed! The image should now be in your SOOT space.")
        
    except Exception as e:
        print(f"[❌] Main function error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()