"""测试 API 和模型可用性"""

from openai import OpenAI
from config import config

client = OpenAI(api_key=config.api.key, base_url=config.api.base_url)

print(f"测试模型：{config.api.model}")
print("-" * 40)

try:
    response = client.chat.completions.create(
        model=config.api.model,
        messages=[{"role": "user", "content": "Hello, just say OK"}],
        temperature=0.2,
        timeout=30,
    )
    print("API 调用成功!")
    print(f"回复：{response.choices[0].message.content}")
except Exception as e:
    print(f"错误：{e}")
