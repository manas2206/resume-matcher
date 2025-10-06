import pdfplumber
from pathlib import Path
import docx

def extract_text_from_file(path: Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    text = ""
    if suffix == ".pdf":
        with pdfplumber.open(path) as pdf:
            for p in pdf.pages:
                text += p.extract_text() or ""
    elif suffix in [".docx", ".doc"]:
        doc = docx.Document(path)
        text = "\n".join([p.text for p in doc.paragraphs])
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
    return text
