import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
from io import BytesIO

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in .env")

# 初始化 Gemini 配置
genai.configure(api_key=API_KEY)

# 使用 Gemini 2.0 Flash 模型
model = genai.GenerativeModel("gemini-2.0-flash-exp-image-generation")

prompt = "A futuristic cyberpunk cat, glowing eyes, dramatic lighting, 4k"

response = model.generate_content(prompt)

# 处理响应内容
for part in response.parts:
    if hasattr(part, "inline_data") and part.inline_data:
        try:
            image_data = part.inline_data.data
            image = Image.open(BytesIO(image_data))
            image.save("output.png")
            print("✅ Image saved as output.png")
        except Exception as e:
            print(f"[❌] Error processing image: {e}")
    elif hasattr(part, "text"):
        print("[📝] Text response:", part.text)
