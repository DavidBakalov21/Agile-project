import uuid
import json
from app.repositories.memory_repo import MemoryRepo
from app.adapters.ollama_client import OllamaClient

class FaqService:
    async def build_faq(self, document_id: str) -> dict:
        doc = MemoryRepo.documents.get(document_id)
        if not doc:
            raise KeyError("Document not found")

        text = (doc.get("text") or "").strip()
        if not text:
            items = [{"q": "What is this document?", "a": "No text extracted yet."}]
        else:
            text_snippet = text[:12000]

            prompt = f"""
Create an FAQ for exam preparation using the document below.

Return ONLY valid JSON in this exact format:
[
  {{"q": "question", "a": "answer"}},
  ...
]

Rules:
- 8 to 12 items
- Questions should cover: grading/exam format, key topics, schedule/modules, important definitions, typical tasks, and how to study.
- Answers must be short and concrete (2-6 sentences).
- If the document doesn’t contain something, say "Not specified in the document."

DOCUMENT:
{text_snippet}
"""
            raw = await OllamaClient().chat(prompt)

            items = self._parse_items(raw)

        faq_id = str(uuid.uuid4())
        MemoryRepo.faqs[faq_id] = {"document_id": document_id, "items": items}
        
        print("OLLAMA_RAW_FIRST_500:", raw[:500])
        return {"faq_id": faq_id, "document_id": document_id, "count": len(items)}

    def _parse_items(self, raw: str):
        raw = raw.strip()

        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            raw = raw[start:end+1]

        data = json.loads(raw)

        items = []
        for it in data:
            if isinstance(it, dict) and "q" in it and "a" in it:
                items.append({"q": str(it["q"]), "a": str(it["a"])})
        if not items:
            raise ValueError("FAQ JSON parsed but had no valid items")
        return items
