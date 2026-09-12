from typing import List


def split_text_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into chunks of roughly `chunk_size` characters, respecting
    paragraph and line boundaries, with the last `overlap` characters of each
    chunk repeated at the start of the next one so context is not cut mid-idea.
    """
    if not text.strip():
        return []
    # Cap the overlap so at least half of every chunk is new content.
    overlap = max(0, min(overlap, chunk_size // 2))

    chunks: List[str] = []
    carry = ""  # tail of the previous chunk, already newline-terminated
    current = ""  # content accumulated since the last emitted chunk

    def emit() -> None:
        nonlocal carry, current
        chunk = (carry + current).strip()
        current = ""
        if not chunk:
            carry = ""
            return
        chunks.append(chunk)
        tail = chunk[-overlap:].lstrip() if overlap else ""
        carry = tail + "\n" if tail else ""

    for para in text.split("\n\n"):
        for line in para.split("\n"):
            if len(carry) + len(current) + len(line) + 1 <= chunk_size:
                current += line + "\n"
            else:
                emit()
                current = line + "\n"
        if current.strip() and len(carry) + len(current) > chunk_size // 2:
            emit()
    if current.strip():
        chunks.append((carry + current).strip())
    return [c for c in chunks if c.strip()]
