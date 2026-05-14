from typing import List


def split_text_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    if not text.strip():
        return []
    paragraphs = text.split("\n\n")
    chunks: List[str] = []
    current = ""
    for para in paragraphs:
        for line in para.split("\n"):
            if len(current) + len(line) + 1 <= chunk_size:
                current += line + "\n"
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = line + "\n"
        if current.strip() and len(current) > chunk_size // 2:
            chunks.append(current.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if c.strip()]
