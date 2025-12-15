from fastapi import FastAPI
from app.api.upload import router as upload_router
from app.api.faq import router as faq_router
from app.api.chat import router as chat_router

app = FastAPI()

@app.get("/")
def root():
    return {"message": "FastAPI is running"}

app.include_router(upload_router)
app.include_router(faq_router)
app.include_router(chat_router)
