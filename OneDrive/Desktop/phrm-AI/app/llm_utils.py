import httpx
from decouple import config

HUGGINGFACE_API_TOKEN = config("HUGGINGFACE_API_TOKEN")
MODEL = "facebook/bart-large-cnn"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"

headers = {
    "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"
}

async def summarize_medical_text(text: str) -> str:
    payload = {
        "inputs": text[:2000],  # Optional: truncate to avoid token limit
        "options": {"wait_for_model": True}
    }

    timeout = httpx.Timeout(60.0)  # ⏱️ increased timeout to 60 seconds

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        if isinstance(result, list) and "summary_text" in result[0]:
            return result[0]["summary_text"]
        else:
            raise Exception("Unexpected response from Hugging Face API")
