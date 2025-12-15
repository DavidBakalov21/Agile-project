from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.ingest_service import IngestService
from app.schemas.models import UploadResponse
from app.repositories.memory_repo import MemoryRepo

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    try:
        return await IngestService().save_and_extract(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/documents/{document_id}")
def get_document(document_id: str):
    doc = MemoryRepo.documents.get(document_id)
    if not doc:
        return {"error": "not found"}
    return {
        "document_id": document_id,
        "filename": doc["filename"],
        "text_preview": (doc.get("text") or "")[:800]
    }