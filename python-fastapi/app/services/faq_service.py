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
        text_snippet = text[:3000]
        
        topics = await self._extract_topics(text_snippet)

        prompt = f"""
        You are an exam-prep tutor.

        Create 10 FAQ items about course TOPICS. Use the topics list as the backbone.
        For each topic, write an exam-like question and a helpful answer.

        Rules:
        - No syllabus logistics.
        - Questions must be about understanding/applying concepts.
        - Output ONLY in:
        Q: ...
        A: ...

        TOPICS:
        {chr(10).join(topics)}

        SYLLABUS SNIPPET (context):
        {text_snippet}
        """.strip()

        raw = await OllamaClient().generate(prompt)
        items = self._parse_qa(raw)

        faq_id = str(uuid.uuid4())
        MemoryRepo.faqs[faq_id] = {"document_id": document_id, "items": items}

        return {"faq_id": faq_id, "document_id": document_id, "count": len(items)}
    
    async def _extract_topics(self, text_snippet: str) -> list[str]:
        prompt = f"""
    Extract a list of 8-12 course CONTENT topics from this syllabus snippet.

    Rules:
    - Only course content topics (concepts, methods, modules).
    - Exclude logistics (grading, deadlines, attendance, schedule).
    - Output ONLY as lines, one topic per line. No numbering.

    SYLLABUS SNIPPET:
    {text_snippet}
    """.strip()

        raw = await OllamaClient().generate(prompt)
        topics = [t.strip("-• \t") for t in raw.splitlines() if t.strip()]
        # keep short and unique
        seen = set()
        cleaned = []
        for t in topics:
            if t.lower() not in seen and len(t) <= 80:
                cleaned.append(t)
                seen.add(t.lower())
        return cleaned[:12]

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