# config.py
import os
import sys
from dotenv import load_dotenv
import openai

# 1. 加载 .env 文件
# override=True 表示如果有同名环境变量，优先使用 .env 中的值
load_dotenv(override=True)

# 2. 读取配置
API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL")
MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-chat") # 默认值

# 3. 检查配置是否存在
if not API_KEY or not BASE_URL:
    print("错误：未在 .env 文件中找到 OPENAI_API_KEY 或 OPENAI_BASE_URL。")
    print("请确保已创建 .env 文件并配置了相关信息。")
    sys.exit(1)

# 4. 初始化全局 Client 实例
# 这样整个项目只需要初始化一次连接
client = openai.OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

print(f"=== 配置加载成功 ===")
print(f"模型: {MODEL_NAME}")
print(f"地址: {BASE_URL}")
print("======================")