from pydantic import BaseModel
import os

class Settings(BaseModel):
    uploads_dir: str = os.getenv("UPLOADS_DIR", "data/uploads")
    processed_dir: str = os.getenv("PROCESSED_DIR", "data/processed")

settings = Settings()
