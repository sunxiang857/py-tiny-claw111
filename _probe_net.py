import os, traceback, winreg
# 子进程未继承 HKCU 环境变量，显式从注册表读取注入
try:
    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
    v, _ = winreg.QueryValueEx(k, "DEEPSEEK_API_KEY")
    os.environ["DEEPSEEK_API_KEY"] = v
except Exception as e:
    print("REG_READ_FAIL:", e)

from openai import OpenAI
api_key = os.getenv("DEEPSEEK_API_KEY")
print("KEY present:", bool(api_key), "len:", len(api_key or ""))
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
try:
    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": "只回复两个字：通了"}],
        max_tokens=16,
    )
    print("NET_OK:", repr(resp.choices[0].message.content))
except Exception as e:
    print("NET_FAIL:", repr(e))
    traceback.print_exc()
