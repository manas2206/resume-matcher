from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import resumes, jobs, match

app = FastAPI(title="Resume Matcher - MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(match.router, prefix="/match", tags=["match"])

@app.get("/health")
def health():
    return {"status": "ok"}
