import time
from fastapi import APIRouter, HTTPException, Query
from app.services.faq_service import FaqService
from app.repositories.memory_repo import MemoryRepo
from app.schemas.models import BuildFaqResponse, FaqResponse
import traceback
import asyncio, uuid
from app.repositories.job_repo import JobRepo

router = APIRouter()
JOB_TTL_SECONDS = 60 * 10  # 10 min

@router.post("/faq/{faq_id}/extend_async")
async def extend_async(faq_id: str):
    faq = MemoryRepo.faqs.get(faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")

    if faq.get("extend_running"):
        return {"job_id": faq.get("extend_job_id"), "already_running": True}

    job_id = str(uuid.uuid4())
    faq["extend_running"] = True
    faq["extend_job_id"] = job_id

    JobRepo.jobs[job_id] = {"status": "running", "faq_id": faq_id, "added": None, "error": None, "ts": time.time()}

    async def runner():
        try:
            res = await FaqService().extend_faq(faq_id)
            JobRepo.jobs[job_id].update(status="done", added=res["added"])
        except Exception as e:
            JobRepo.jobs[job_id].update(status="error", error=repr(e))
        finally:
            faq["extend_running"] = False

    asyncio.create_task(runner())
    return {"job_id": job_id}

@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    now = time.time()
    # cleanup old jobs
    for jid, job in list(JobRepo.jobs.items()):
        if now - job.get("ts", now) > JOB_TTL_SECONDS:
            JobRepo.jobs.pop(jid, None)

    job = JobRepo.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

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

