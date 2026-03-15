import os
from dotenv import load_dotenv
import requests

load_dotenv()

def check_all_models():
    token = os.getenv("GITHUB_TOKEN")
    models = [
        "gpt-4o", 
        "gpt-4o-mini", 
        "meta-llama-3.1-405b-instruct",
        "meta-llama-3.1-70b-instruct",
        "meta-llama-3-8b-instruct",
        "Phi-3-medium-4k-instruct"
    ]
    
    print(f"Checking models for Token ending in ...{token[-4:]}")

    for model in models:
        url = "https://models.github.io/inference/chat/completions" if "llama" in model.lower() else "https://models.github.ai/inference/chat/completions"
        # Wait, the URL is usually the same for all in GitHub Models
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
                print(f"✅ {model}: WORKING")
            else:
                print(f"❌ {model}: FAILED (Status {response.status_code})")
        except Exception as e:
            print(f"ERROR {model}: {e}")

if __name__ == "__main__":
    check_all_models()
