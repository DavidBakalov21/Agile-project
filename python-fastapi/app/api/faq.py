from fastapi import APIRouter, HTTPException
from app.services.faq_service import FaqService
from app.repositories.memory_repo import MemoryRepo
from app.schemas.models import BuildFaqResponse, FaqResponse
import traceback

router = APIRouter()

@router.post("/documents/{document_id}/build_faq")
async def build_faq(document_id: str):
    try:
        return await FaqService().build_faq(document_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        traceback.print_exc()  # <-- prints full stack trace in docker logs
        raise HTTPException(status_code=400, detail=repr(e))  # <-- not empty

@router.get("/faq/{faq_id}", response_model=FaqResponse)
def get_faq(faq_id: str):
    faq = MemoryRepo.faqs.get(faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return {"faq_id": faq_id, "document_id": faq["document_id"], "items": faq["items"]}
