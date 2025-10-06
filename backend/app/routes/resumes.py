# backend/app/routes/resumes.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import uuid
from app.utils import extract_text_from_file
from app.embeddings import add_resume, get_all_resumes, delete_resume, rebuild_index_from_files
from app.embeddings import EMB_DIR, INDEX_PATH  # import paths for download

router = APIRouter()

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "resumes"
DATA_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    uid = str(uuid.uuid4())
    out_path = DATA_DIR / f"{uid}_{file.filename}"
    contents = await file.read()
    out_path.write_bytes(contents)
    text = extract_text_from_file(out_path)
    rid = add_resume(uid, file.filename, text)
    return {"id": rid, "filename": file.filename, "text_snippet": text[:300]}

@router.get("/", summary="List indexed resumes")
def list_resumes():
    return {"resumes": get_all_resumes()}

@router.delete("/{resume_id}", summary="Delete a resume by id")
def remove_resume(resume_id: str):
    ok = delete_resume(resume_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"status": "deleted", "id": resume_id}

@router.post("/rebuild", summary="Rebuild index from files in data/resumes")
def rebuild_from_files():
    count = rebuild_index_from_files(DATA_DIR)
    return {"status": "rebuild_done", "added": count}

@router.get("/index", summary="Download index.json (embeddings metadata)")
def download_index():
    """
    Returns the embeddings/index.json file for download so frontend can inspect it.
    """
    if INDEX_PATH.exists():
        # FileResponse will stream the file for download
        return FileResponse(INDEX_PATH, filename="index.json", media_type="application/json")
    else:
        return JSONResponse({"error": "index not found"}, status_code=404)
