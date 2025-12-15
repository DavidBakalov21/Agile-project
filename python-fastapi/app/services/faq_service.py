import uuid
from app.repositories.memory_repo import MemoryRepo

class FaqService:
    def build_faq(self, document_id: str) -> dict:
        doc = MemoryRepo.documents.get(document_id)
        if not doc:
            raise KeyError("Document not found")

        text = (doc.get("text") or "").strip()
        if not text:
            items = [{"q": "What is this document?", "a": "No text extracted yet."}]
        else:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            items = []

            items.append({
                "q": "What is this course about (summary)?",
                "a": "This is a rough auto-summary based on the uploaded text. Replace with LLM later."
            })

            # If syllabus has headings like "Week", "Module", "Exam", pick some:
            keywords = ["exam", "grading", "assessment", "week", "module", "topic", "literature", "reading"]
            found = [ln for ln in lines if any(k in ln.lower() for k in keywords)]
            if found:
                items.append({
                    "q": "What are the key topics / structure mentioned?",
                    "a": "\n".join(found[:12])
                })
            else:
                items.append({
                    "q": "What are the key topics / structure mentioned?",
                    "a": "\n".join(lines[:12])
                })

            items.append({
                "q": "How should I prepare first?",
                "a": "Start by listing topics/week sections, then generate practice questions per topic."
            })

        faq_id = str(uuid.uuid4())
        MemoryRepo.faqs[faq_id] = {
            "document_id": document_id,
            "items": items
        }
        return {"faq_id": faq_id, "document_id": document_id, "count": len(items)}
