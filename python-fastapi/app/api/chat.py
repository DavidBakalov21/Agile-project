from fastapi import APIRouter, HTTPException
import traceback

from app.services.chat_service import ChatService
from app.schemas.models import ChatRequest, ChatResponse

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        return await ChatService().answer(req.document_id, req.question)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        traceback.print_exc()
        # repr(e) avoids empty "detail": ""
        raise HTTPException(status_code=400, detail=repr(e))
