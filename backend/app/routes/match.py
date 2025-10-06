from fastapi import APIRouter
from app.embeddings import match_current_job, get_all_resumes

router = APIRouter()

@router.get("/top")
def top_matches(n: int = 5):
    matches = match_current_job(top_k=n)
    # matches: list of dicts {id, filename, score, snippet}
    return {"matches": matches, "count": len(matches)}

@router.get("/resumes")
def list_resumes():
    return {"resumes": get_all_resumes()}
