# backend/app/embeddings.py
from sentence_transformers import SentenceTransformer, util
import threading
import numpy as np
import re
import json
from pathlib import Path
import uuid
import hashlib
from typing import Dict

MODEL_NAME = "all-MiniLM-L6-v2"
_MODEL = None
_MODEL_LOCK = threading.Lock()

def get_model():
    global _MODEL
    with _MODEL_LOCK:
        if _MODEL is None:
            _MODEL = SentenceTransformer(MODEL_NAME)
    return _MODEL

# storage paths
BASE_DIR = Path(__file__).resolve().parents[2]   # backend/
EMB_DIR = BASE_DIR / "data" / "embeddings"
EMB_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = EMB_DIR / "index.json"

SENT_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')

def split_into_sentences(text):
    if not text:
        return []
    sents = [s.strip() for s in SENT_SPLIT_RE.split(text) if s.strip()]
    if len(sents) <= 1:
        sents = [s.strip() for s in text.splitlines() if s.strip()]
    return sents[:200]

# in-memory store
_RESUMES: Dict[str, dict] = {}
_CURRENT_JOB = {"text": None, "embedding": None, "sent_embs": None}

# ---------------- Persistence helpers ----------------
def _index_to_disk():
    meta = {}
    for rid, v in _RESUMES.items():
        meta[rid] = {
            "filename": v["filename"],
            "text": v["text"],
            "sentences": v["sentences"],
        }
        # save embeddings as .npy
        np.save(EMB_DIR / f"{rid}_sent_embs.npy", v["sentence_embeddings"])
        np.save(EMB_DIR / f"{rid}_doc_emb.npy", v["doc_embedding"])
    with INDEX_PATH.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def _load_index_from_disk():
    if not INDEX_PATH.exists():
        return 0
    try:
        with INDEX_PATH.open("r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return 0

    loaded = 0
    for rid, info in meta.items():
        sent_path = EMB_DIR / f"{rid}_sent_embs.npy"
        doc_path = EMB_DIR / f"{rid}_doc_emb.npy"
        if sent_path.exists() and doc_path.exists():
            try:
                sent_embs = np.load(sent_path)
                doc_emb = np.load(doc_path)
            except Exception:
                continue
            _RESUMES[rid] = {
                "filename": info.get("filename"),
                "text": info.get("text"),
                "sentences": info.get("sentences", []),
                "sentence_embeddings": np.asarray(sent_embs, dtype=np.float32),
                "doc_embedding": np.asarray(doc_emb, dtype=np.float32),
            }
            loaded += 1
    return loaded

# ---------------- Core functions ----------------
def _make_id_from_file(path: Path):
    """
    Deterministic id based on file contents to avoid duplicates across rebuilds.
    """
    data = path.read_bytes()
    h = hashlib.sha1(data).hexdigest()
    return f"file-{h}"

def add_resume(resume_id, filename, text):
    """
    Add resume, compute embeddings, persist to disk.
    If resume_id is None or empty, generate a uuid.
    """
    if not resume_id:
        resume_id = str(uuid.uuid4())
    model = get_model()
    sentences = split_into_sentences(text)
    if len(sentences) == 0:
        sentences = [text[:512]]
    sent_embs = model.encode(sentences, convert_to_numpy=True, show_progress_bar=False)
    doc_emb = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
    _RESUMES[resume_id] = {
        "filename": filename,
        "text": text,
        "sentences": sentences,
        "sentence_embeddings": np.asarray(sent_embs, dtype=np.float32),
        "doc_embedding": np.asarray(doc_emb, dtype=np.float32),
    }
    _index_to_disk()
    return resume_id

def delete_resume(resume_id: str) -> bool:
    """
    Remove a resume from memory and disk. Returns True if deleted.
    """
    if resume_id not in _RESUMES:
        return False
    # remove npy files
    sent_path = EMB_DIR / f"{resume_id}_sent_embs.npy"
    doc_path = EMB_DIR / f"{resume_id}_doc_emb.npy"
    try:
        if sent_path.exists():
            sent_path.unlink()
        if doc_path.exists():
            doc_path.unlink()
    except Exception:
        pass
    # remove from memory
    _RESUMES.pop(resume_id, None)
    # re-write index
    _index_to_disk()
    return True

def rebuild_index_from_files(resume_folder: Path):
    """
    Scan `resume_folder` for text/pdf/docx files and add missing ones to index.
    Uses deterministic id from file contents to prevent duplicates.
    Returns number of new files added.
    """
    count = 0
    files = list(resume_folder.glob("*"))
    for f in files:
        if not f.is_file():
            continue
        # only handle .txt/.pdf/.docx/.doc for now
        if f.suffix.lower() not in [".txt", ".pdf", ".docx", ".doc"]:
            continue
        rid = _make_id_from_file(f)
        # skip if already present
        if rid in _RESUMES:
            continue
        # read text (simple for txt; for pdf/docx you may want to reuse utils.extract_text_from_file)
        try:
            if f.suffix.lower() == ".txt":
                text = f.read_text(encoding="utf-8", errors="ignore")
            else:
                # lazy import to avoid circular dependency if utils uses embeddings
                from app.utils import extract_text_from_file
                text = extract_text_from_file(f)
        except Exception:
            continue
        add_resume(rid, f.name, text)
        count += 1
    return count

def get_all_resumes():
    return [{"id": k, "filename": v["filename"]} for k, v in _RESUMES.items()]

def set_current_job(job_text):
    model = get_model()
    _CURRENT_JOB["text"] = job_text
    _CURRENT_JOB["embedding"] = np.asarray(model.encode(job_text, convert_to_numpy=True), dtype=np.float32)
    job_sents = split_into_sentences(job_text)
    if not job_sents:
        job_sents = [job_text[:512]]
    _CURRENT_JOB["sent_embs"] = np.asarray(model.encode(job_sents, convert_to_numpy=True), dtype=np.float32)
    _CURRENT_JOB["sentences"] = job_sents

def match_current_job(top_k=5):
    if _CURRENT_JOB["embedding"] is None:
        return []

    results = []
    q_doc = _CURRENT_JOB["embedding"]
    q_sent_embs = _CURRENT_JOB.get("sent_embs", None)

    for rid, r in _RESUMES.items():
        doc_sim = float(util.cos_sim(q_doc, r["doc_embedding"]).numpy().reshape(-1)[0])
        sent_sim = 0.0
        best_pair = ("", 0.0)
        if q_sent_embs is not None and r["sentence_embeddings"].size > 0:
            cs = util.cos_sim(q_sent_embs, r["sentence_embeddings"])
            if hasattr(cs, "numpy"):
                cs = cs.numpy()
            cs_arr = np.asarray(cs)
            max_idx = np.unravel_index(np.argmax(cs_arr), cs_arr.shape)
            max_val = float(cs_arr[max_idx])
            sent_sim = max_val
            best_resume_sent = r["sentences"][max_idx[1]]
            best_pair = (best_resume_sent, max_val)
        score = 0.7 * sent_sim + 0.3 * doc_sim
        snippet = best_pair[0] if best_pair[1] > 0.05 else (r["text"][:300].replace("\n", " "))
        results.append({"id": rid, "filename": r["filename"], "score": float(score), "snippet": snippet})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

# ---------------- Initialization: load persisted index ----------------
_loaded = _load_index_from_disk()
if _loaded:
    print(f"[embeddings] Loaded {_loaded} resumes from disk index.")
else:
    print("[embeddings] No persisted resumes found (index empty).")
