from fastapi import APIRouter, HTTPException
from app.services.chat_service import ChatService
from app.schemas.models import ChatRequest, ChatResponse

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        return ChatService().answer(req.document_id, req.question)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
