# services/ai_service.py

import requests
from django.conf import settings


def ask_ai(prompt):
    response = requests.post(
        f"{settings.AI_API_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.AI_API_KEY}"
        },
        json={
            "model": "auto",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        },
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"]