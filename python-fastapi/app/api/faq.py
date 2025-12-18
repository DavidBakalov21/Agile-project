from fastapi import APIRouter, HTTPException, Query
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


@router.get("/faq/{faq_id}")
def get_faq(
    faq_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=20),
):
    faq = MemoryRepo.faqs.get(faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")

    items = faq["items"]
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size

    page_items = items[start:end]
    total_pages = (total + page_size - 1) // page_size

    return {
        "faq_id": faq_id,
        "document_id": faq["document_id"],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "items": page_items,
    }

