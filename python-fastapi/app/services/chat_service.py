# app/services/chat_service.py
import re
from typing import List, Tuple

from app.repositories.memory_repo import MemoryRepo
from app.adapters.ollama_client import OllamaClient

STOPWORDS = {
    "the","and","for","with","that","this","from","into","your","you","are","was","were","will",
    "have","has","had","they","them","their","then","than","when","what","why","how","where",
    "can","could","should","would","about","also","not","but","its","it's","as","on","in","to",
    "of","a","an","is","be","by","or","at","it"
}

LOGISTICS_HINTS = {
    "grading","deadline","attendance","schedule","office hours","zoom","link","submission",
    "exam date","date","time","room","campus","policy","late","assignment due","rubric"
}

def _strip_model_noise(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()

class ChatService:
    async def answer(self, document_id: str, question: str) -> dict:
        doc = MemoryRepo.documents.get(document_id)
        if not doc:
            raise KeyError("Document not found")

        text = (doc.get("text") or "").strip()
        if not text:
            return {"answer": "Your document text is empty.", "matched_snippet": None}

        q = (question or "").strip()
        if not q:
            return {"answer": "Ask a question first 🙂", "matched_snippet": None}

        chunks = self._chunk_text(text)
        top = self._retrieve_top_chunks(chunks, q, k=4)
        context = "\n\n---\n\n".join([c for (c, _score) in top]) if top else text[:2000]

        asks_logistics = any(h in q.lower() for h in LOGISTICS_HINTS)

        system = (
            "You are a helpful course tutor.\n"
            "Default: focus on COURSE CONTENT (concepts, methods, comparisons, applications, examples).\n"
            "Only answer logistics (deadlines, grading, schedule) if the user explicitly asks.\n"
            "If the provided context is insufficient, say what key term/topic is missing and suggest what to search for."
        )

        user_prompt = f"""
QUESTION:
{q}

CONTEXT (from the user materials):
{context}

INSTRUCTIONS:
- If this is a content question: define, compare, and give a small example.
- If this is a logistics question: answer directly using context.
""".strip()

        raw = await self._safe_ollama_chat(system, user_prompt)
        answer = _strip_model_noise(raw)

        # show first top chunk as "matched"
        matched = top[0][0] if top else None

        return {"answer": answer, "matched_snippet": matched}

    async def _safe_ollama_chat(self, system: str, user_prompt: str) -> str:
        # embed system into user prompt (since your OllamaClient.chat has a fixed system message)
        prompt = f"SYSTEM:\n{system}\n\n{user_prompt}"
        return await OllamaClient().chat(prompt)

    def _chunk_text(self, text: str, max_chars: int = 900, overlap: int = 120) -> List[str]:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        chunks = []
        i = 0
        n = len(text)
        while i < n:
            end = min(i + max_chars, n)
            chunk = text[i:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == n:
                break
            i = max(end - overlap, i + 1)
        return chunks

    def _keywords(self, question: str) -> List[str]:
        toks = re.findall(r"[a-zA-Z0-9]+", question.lower())
        kws = [t for t in toks if len(t) >= 4 and t not in STOPWORDS]
        seen, out = set(), []
        for w in kws:
            if w not in seen:
                seen.add(w)
                out.append(w)
        return out[:18]

    def _retrieve_top_chunks(self, chunks: List[str], question: str, k: int = 4) -> List[Tuple[str, int]]:
        kws = self._keywords(question)
        if not kws:
            return [(c, 0) for c in chunks[:k]]

        scored = []
        for c in chunks:
            cl = c.lower()
            score = sum(1 for w in kws if w in cl)
            if score > 0:
                scored.append((c, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
