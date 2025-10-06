from fastapi import APIRouter
from pydantic import BaseModel
from app.embeddings import set_current_job

router = APIRouter()

class JobIn(BaseModel):
    title: str = None
    description: str

@router.post("/upload")
def upload_job(job: JobIn):
    jd_text = (job.title or "") + "\n" + job.description
    set_current_job(jd_text)
    return {"status": "job_received", "snippet": jd_text[:300]}
