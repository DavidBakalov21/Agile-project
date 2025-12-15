from pathlib import Path

def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")

    return f"[Text extraction not implemented for {suffix}. Upload a .txt for now.]"
