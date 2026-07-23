from pathlib import Path


def load_and_validate_document(file_path: str) -> str:
    """Makes sure the document loads correctly and in the correct format"""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found at {file_path}")

    if path.suffix.lower() != ".txt":
        raise ValueError("Only '.txt' files are supported.")

    text = path.read_text(encoding="utf-8").strip()

    if not text:
        raise ValueError("Document is empty.")

    # print("Document successfully load :)")

    return text
