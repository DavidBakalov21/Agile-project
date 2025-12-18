import uuid
from app.repositories.memory_repo import MemoryRepo
from app.adapters.ollama_client import OllamaClient

class FaqService:
    async def build_faq(self, document_id: str) -> dict:
        doc = MemoryRepo.documents.get(document_id)
        if not doc:
            raise KeyError("Document not found")

        text = (doc.get("text") or "")
        text = " ".join(text.split())
        text_snippet = text[:3000]  # start smaller, safer

        prompt = f"""
Generate 8 exam-prep FAQ items from the document snippet.

Return ONLY this format (no markdown):
Q: ...
A: ...

DOCUMENT SNIPPET:
{text_snippet}
""".strip()

        raw = await OllamaClient().generate(prompt)

        print("OLLAMA_RAW_FIRST_500:", raw[:500])

        items = self._parse_qa(raw)

        faq_id = str(uuid.uuid4())
        MemoryRepo.faqs[faq_id] = {"document_id": document_id, "items": items}

        return {"faq_id": faq_id, "document_id": document_id, "count": len(items)}

    def _parse_qa(self, raw: str):
        items = []
        cur_q = None
        cur_a = None

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("Q:"):
                if cur_q and cur_a:
                    items.append({"q": cur_q.strip(), "a": cur_a.strip()})
                cur_q = line[2:].strip()
                cur_a = ""
                continue

            if line.startswith("A:") and cur_q is not None:
                cur_a = line[2:].strip()
                continue

            # continuation line
            if cur_q is not None and cur_a is not None:
                cur_a += " " + line

        if cur_q and cur_a:
            items.append({"q": cur_q.strip(), "a": cur_a.strip()})

        if not items:
            raise ValueError(f"Model returned no FAQ items. Raw starts with: {raw[:200]!r}")

        # keep only first 8 if model produced more
        return items[:8]