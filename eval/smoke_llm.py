"""Smoke: COMETAPI_KEY + LLMClient path + usage capture feasibility."""
import json, os, urllib.request

key = os.environ["COMETAPI_KEY"]
base = os.environ.get("LLM_BASE_URL", "https://api.cometapi.com/v1")
model = os.environ.get("LLM_MODEL", "deepseek-v4-flash-vision-exp")
body = json.dumps({
    "model": model,
    "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
    "max_tokens": 8,
}).encode()
req = urllib.request.Request(f"{base}/chat/completions", data=body, headers={
    "Content-Type": "application/json", "Authorization": f"Bearer {key}"})
with urllib.request.urlopen(req, timeout=60) as resp:
    data = json.loads(resp.read().decode())
print("content:", data["choices"][0]["message"]["content"])
print("model:", data.get("model"))
print("usage:", json.dumps(data.get("usage", {})))
