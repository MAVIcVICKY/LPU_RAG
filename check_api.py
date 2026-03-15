import os
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

def check_github_api():
    token = os.getenv("GITHUB_TOKEN")
    model = os.getenv("GITHUB_MODEL", "gpt-4o")
    
    if not token:
        print("ERROR: GITHUB_TOKEN not found in .env file!")
        return

    print(f"Checking GitHub API with Token: {token[:6]}...{token[-4:]}")
    print(f"Model: {model}")

    url = "https://models.github.ai/inference/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = {
        "messages": [{"role": "user", "content": "Say hello"}],
        "model": model,
        "max_tokens": 10
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            print("SUCCESS: API is working perfectly!")
            print(f"Response: {response.json()['choices'][0]['message']['content']}")
        elif response.status_code == 429:
            print("FAILED: Too Many Requests (Rate Limit Exceeded).")
            print("Reason: You have exhausted your free GitHub Models quota.")
        elif response.status_code == 401:
            print("FAILED: Unauthorized. Your GITHUB_TOKEN is invalid or expired.")
        else:
            print(f"FAILED: Status {response.status_code}")
            print(f"Error Message: {response.text}")
            
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")

if __name__ == "__main__":
    check_github_api()
