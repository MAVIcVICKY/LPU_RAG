import os
from dotenv import load_dotenv
import requests

load_dotenv()

def check_models():
    token = os.getenv("GITHUB_TOKEN")
    models = ["gpt-4o", "gpt-4o-mini", "meta-llama-3.1-405b-instruct"]
    
    print(f"Checking multiple models for Token: {token[:10]}...")

    for model in models:
        url = "https://models.github.ai/inference/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        data = {
            "messages": [{"role": "user", "content": "Hi"}],
            "model": model,
            "max_tokens": 5
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                print(f"✅ SUCCESS with {model}")
                return model
            else:
                print(f"❌ FAILED with {model}: Status {response.status_code}")
        except Exception as e:
            print(f"ERROR with {model}: {e}")
    return None

if __name__ == "__main__":
    check_models()
