from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.ingest_service import IngestService
from app.schemas.models import UploadResponse

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    try:
        return await IngestService().save_and_extract(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
