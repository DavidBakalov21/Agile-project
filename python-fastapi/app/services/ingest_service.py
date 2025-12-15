import uuid
from pathlib import Path
from fastapi import UploadFile
from app.core.config import settings
from app.services.extractors import extract_text_from_file
from app.repositories.memory_repo import MemoryRepo

class IngestService:
    def __init__(self):
        self.uploads_dir = Path(settings.uploads_dir)
        self.processed_dir = Path(settings.processed_dir)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    async def save_and_extract(self, file: UploadFile) -> dict:
        doc_id = str(uuid.uuid4())
        safe_name = file.filename.replace("/", "_").replace("\\", "_")
        upload_path = self.uploads_dir / f"{doc_id}__{safe_name}"

        content = await file.read()
        upload_path.write_bytes(content)

        text = extract_text_from_file(upload_path)
        text_path = self.processed_dir / f"{doc_id}.txt"
        text_path.write_text(text, encoding="utf-8")

        MemoryRepo.documents[doc_id] = {
            "filename": file.filename,
            "path": str(upload_path),
            "text_path": str(text_path),
            "text": text,
        }
        return {"document_id": doc_id, "filename": file.filename}
