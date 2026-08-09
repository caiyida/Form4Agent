import os
from dotenv import load_dotenv

# 读取项目根目录的 .env
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if api_key:
    print("✅ API Key loaded successfully!")
    print(api_key[:12] + "...")
else:
    print("❌ API Key not found!")