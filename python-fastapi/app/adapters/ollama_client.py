import os
import httpx

class OllamaClient:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        
    async def generate(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            # keep it short so it finishes fast
            "options": {
                "temperature": 0.2,
                "num_predict": 600,
                "num_ctx": 2048
            }
        }
        async with httpx.AsyncClient(timeout=180) as client:  # 3 minutes
            r = await client.post(url, json=payload)
            r.raise_for_status()
            return r.json()["response"]

    async def generate_json(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "num_ctx": 2048
            }
        }
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            return r.json()["response"]


    async def chat(self, prompt: str) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that outputs ONLY valid JSON when asked."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            return data["message"]["content"]
