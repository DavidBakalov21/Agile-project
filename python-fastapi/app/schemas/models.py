from pydantic import BaseModel
from typing import List, Optional

class UploadResponse(BaseModel):
    document_id: str
    filename: str

class BuildFaqResponse(BaseModel):
    faq_id: str
    document_id: str
    count: int

class FaqItem(BaseModel):
    q: str
    a: str

class FaqResponse(BaseModel):
    faq_id: str
    document_id: str
    items: List[FaqItem]

class ChatRequest(BaseModel):
    document_id: str
    question: str

class ChatResponse(BaseModel):
    answer: str
    matched_snippet: Optional[str] = None
