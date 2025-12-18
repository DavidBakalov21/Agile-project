import uuid
from typing import List, Dict, Any

from app.repositories.memory_repo import MemoryRepo
from app.adapters.ollama_client import OllamaClient
from app.utils.helpers import _q_hash, _norm_q


class FaqService:
    PAGE_SIZE = 5
    MAX_PAGES = 5

    async def build_faq(self, document_id: str) -> dict:
        doc = MemoryRepo.documents.get(document_id)
        if not doc:
            raise KeyError("Document not found")

        text = (doc.get("text") or "")
        text = " ".join(text.split())
        text_snippet = text[:3000]

        topics = await self._extract_topics(text_snippet)
        if not topics:
            topics = [
                "Key concepts and definitions",
                "Core models/frameworks",
                "Common exam-style applications",
            ]

        print("TOPICS:", topics)

        base_prompt = f"""
You are an exam-prep tutor.

Generate {self.PAGE_SIZE} DISTINCT study FAQ items based on the COURSE TOPICS listed below.

Rules:
- Each question MUST relate to one of the topics.
- Do NOT focus on syllabus logistics (grading, deadlines, schedule, attendance, office hours).
- Questions must be exam-like (define/compare/apply).
- Answers: 3–6 sentences, include one example when possible.
- No duplicates.

Output format ONLY:
Q: ...
A: ...

COURSE TOPICS:
{chr(10).join(f"- {t}" for t in topics)}

SYLLABUS CONTEXT (reference only):
{text_snippet}
""".strip()

        raw = await OllamaClient().generate(base_prompt)
        items = self._parse_qa(raw)

        # Strong dedupe for first page
        seen_hashes = set()
        filtered: List[Dict[str, str]] = []
        for it in items:
            h = _q_hash(it["q"])
            if h not in seen_hashes:
                seen_hashes.add(h)
                filtered.append(it)

        items = filtered[: self.PAGE_SIZE]

        # Top up to PAGE_SIZE (with explicit "do not repeat" list)
        if len(items) < self.PAGE_SIZE:
            existing_qs = "\n".join(f"- {it['q']}" for it in items)
            need = self.PAGE_SIZE - len(items)

            prompt2 = f"""
{base_prompt}

EXISTING QUESTIONS (do NOT repeat or paraphrase):
{existing_qs}

Generate {need} MORE NEW items.
""".strip()

            raw2 = await OllamaClient().generate(prompt2)
            more = self._parse_qa(raw2)
            for it in more:
                h = _q_hash(it["q"])
                if h not in seen_hashes:
                    items.append(it)
                    seen_hashes.add(h)
                if len(items) >= self.PAGE_SIZE:
                    break

        faq_id = str(uuid.uuid4())
        MemoryRepo.faqs[faq_id] = {
            "document_id": document_id,
            "topics": topics,
            "text_snippet": text_snippet,
            "items": items,
            # store as LIST (JSON-friendly), convert to set when needed
            "seen": list(seen_hashes),
        }

        return {"faq_id": faq_id, "document_id": document_id, "count": len(items)}

    async def extend_faq(self, faq_id: str) -> dict:
        faq = MemoryRepo.faqs.get(faq_id)
        if not faq:
            raise KeyError("FAQ not found")

        items: List[Dict[str, str]] = faq.get("items", [])
        max_items = self.MAX_PAGES * self.PAGE_SIZE
        if len(items) >= max_items:
            return {"faq_id": faq_id, "added": 0, "total": len(items), "max_reached": True}

        topics = faq.get("topics", [])
        text_snippet = faq.get("text_snippet", "")

        # Avoid duplicates: give model existing questions
        existing_qs = "\n".join(f"- {it['q']}" for it in items[:50])

        # Strong dedupe using stored hashes (list -> set)
        seen_list = faq.get("seen", [])
        seen = set(seen_list)

        print(f"[extend_faq] faq_id={faq_id} current_items={len(items)}")

        prompt = f"""
You are an exam-prep tutor.

Generate {self.PAGE_SIZE} NEW and DISTINCT study FAQ items based on the COURSE TOPICS below.

Hard rules:
- Do NOT repeat or paraphrase any existing questions.
- Do NOT focus on syllabus logistics.
- Each question must clearly map to one topic.
- Output ONLY:
TOPIC: <one of the topics>
Q: ...
A: ...

COURSE TOPICS:
{chr(10).join(f"- {t}" for t in topics)}

EXISTING QUESTIONS (do NOT repeat):
{existing_qs}

SYLLABUS CONTEXT (reference only):
{text_snippet}
""".strip()

        raw = await OllamaClient().generate(prompt)
        new_items = self._parse_qa(raw)

        added_items: List[Dict[str, str]] = []
        for it in new_items:
            h = _q_hash(it["q"])
            if h in seen:
                continue
            added_items.append(it)
            seen.add(h)
            if len(added_items) >= self.PAGE_SIZE:
                break

        faq["items"].extend(added_items)
        faq["seen"] = list(seen)  # persist back as list

        total = len(faq["items"])
        return {
            "faq_id": faq_id,
            "added": len(added_items),
            "total": total,
            "max_reached": total >= max_items,
        }

    async def _extract_topics(self, text_snippet: str) -> List[str]:
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

        # keep short and unique (case-insensitive)
        seen = set()
        cleaned: List[str] = []
        for t in topics:
            key = t.lower()
            if key not in seen and len(t) <= 80:
                cleaned.append(t)
                seen.add(key)

        return cleaned[:12]

    def _parse_qa(self, raw: str) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        cur_q = None
        cur_a = None

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue

            # model may include topic lines; ignore them (or parse if you want later)
            if line.startswith("TOPIC:"):
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