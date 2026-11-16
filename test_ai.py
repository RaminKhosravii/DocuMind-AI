import requests

print("Connecting to Ollama...", flush=True)

try:
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "gemma3:1b",
            "messages": [
                {
                    "role": "user",
                    "content": "سلام، فقط بگو اتصال موفق بود."
                }
            ],
            "stream": False
        },
        timeout=120
    )

    response.raise_for_status()

    result = response.json()
    print("\nAI Response:")
    print(result["message"]["content"])

except Exception as error:
    print("ERROR:", error)