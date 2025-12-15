from app.repositories.memory_repo import MemoryRepo

class ChatService:
    def answer(self, document_id: str, question: str) -> dict:
        doc = MemoryRepo.documents.get(document_id)
        if not doc:
            raise KeyError("Document not found")

        text = doc.get("text") or ""
        q = question.strip().lower()

        words = [w for w in q.split() if len(w) >= 4]
        best = None
        for ln in text.splitlines():
            l = ln.strip()
            if not l:
                continue
            if any(w in l.lower() for w in words):
                best = l
                break

        if best:
            answer = f"Based on your materials, this line seems relevant:\n\n{best}"
            return {"answer": answer, "matched_snippet": best}

        return {
            "answer": "I couldn't find a direct match in the extracted text. Try asking with keywords from the syllabus (e.g., 'grading', 'exam', 'week 3').",
            "matched_snippet": None
        }
