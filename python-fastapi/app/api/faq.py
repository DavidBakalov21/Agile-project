from fastapi import APIRouter, HTTPException
from app.services.faq_service import FaqService
from app.repositories.memory_repo import MemoryRepo
from app.schemas.models import BuildFaqResponse, FaqResponse

router = APIRouter()

@router.post("/documents/{document_id}/build_faq", response_model=BuildFaqResponse)
def build_faq(document_id: str):
    try:
        return FaqService().build_faq(document_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/faq/{faq_id}", response_model=FaqResponse)
def get_faq(faq_id: str):
    faq = MemoryRepo.faqs.get(faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return {"faq_id": faq_id, "document_id": faq["document_id"], "items": faq["items"]}
