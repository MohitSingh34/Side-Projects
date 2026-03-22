import requests
import json

def test_deepseek_api():
    # Tera server port 8002 pe chal raha hai
    url = "http://127.0.0.1:8000/v1/chat/completions"

    # OpenAI standard format jo tera server accept karta hai
    payload = {
        "model": "perplexity-scraper",
        "messages": [
            {
                "role": "user",
                "content": "ok"
            }
        ]
    }

    headers = {
        "Content-Type": "application/json"
    }

    print("⏳ Sending message to DeepSeek server...")
    print(f"Prompt: '{payload['messages'][0]['content']}'\n")

    try:
        # Request bhej rahe hain
        response = requests.post(url, json=payload, headers=headers)

        # Agar status code 200 nahi hai toh error throw karega
        response.raise_for_status()

        # JSON response nikal ke sundar tarike se print karna
        response_data = response.json()

        print("✅ Response Received!\n")
        print("=== RAW JSON OUTPUT ===")
        print(json.dumps(response_data, indent=4, ensure_ascii=False))

    except requests.exceptions.ConnectionError:
        print("❌ Error: Server se connect nahi ho paya. Kya deepseek.py chal raha hai port 8002 pe?")
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error aayi: {e}")
        print("Server Message:", response.text)
    except Exception as e:
        print(f"❌ Kuch aur error aayi: {e}")

if __name__ == "__main__":
    test_deepseek_api()
