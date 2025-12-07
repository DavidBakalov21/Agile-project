from fastapi import FastAPI, UploadFile, File

app = FastAPI()

@app.get("/")
def root():
    return {"message": "FastAPI is running"}

@app.post("/upload")
async def process_file(file: UploadFile = File(...)):
    return {"filename": file.filename}