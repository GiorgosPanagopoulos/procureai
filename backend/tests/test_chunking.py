from rag.chunking import split_text_chunks


def test_empty_string():
    assert split_text_chunks("") == []


def test_whitespace_only():
    assert split_text_chunks("   \n\n  \t  ") == []


def test_single_short_paragraph():
    result = split_text_chunks("Hello World")
    assert len(result) == 1
    assert result[0] == "Hello World"


def test_long_text_splits_into_multiple():
    line = "A" * 100
    text = "\n\n".join([line] * 10)
    chunks = split_text_chunks(text, chunk_size=200)
    assert len(chunks) > 1


def test_custom_chunk_size_produces_more_chunks():
    line = "word " * 10  # ~50 chars per line
    text = "\n".join([line] * 20)
    small_chunks = split_text_chunks(text, chunk_size=100)
    default_chunks = split_text_chunks(text, chunk_size=500)
    assert len(small_chunks) >= len(default_chunks)


def test_chunks_not_excessively_large():
    short_line = "Hello World "  # 12 chars
    text = "\n".join([short_line] * 100)
    chunk_size = 100
    chunks = split_text_chunks(text, chunk_size=chunk_size)
    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk) <= chunk_size * 2


def _numbered_lines(count: int = 20) -> str:
    """Lines that are long enough to force splitting and unique enough to trace."""
    return "\n".join(f"line-{i:03d} " + "x" * 40 for i in range(count))


def test_overlap_repeats_tail_of_previous_chunk():
    overlap = 40
    chunks = split_text_chunks(_numbered_lines(), chunk_size=200, overlap=overlap)
    assert len(chunks) > 1
    for prev, nxt in zip(chunks, chunks[1:]):
        tail = prev[-overlap:].lstrip()
        assert tail
        assert nxt.startswith(tail), f"chunk does not carry the previous tail: {nxt[:80]!r}"


def test_zero_overlap_does_not_repeat_text():
    chunks = split_text_chunks(_numbered_lines(), chunk_size=200, overlap=0)
    assert len(chunks) > 1
    for prev, nxt in zip(chunks, chunks[1:]):
        assert not nxt.startswith(prev[-40:].lstrip())


def test_overlap_is_capped_at_half_the_chunk_size():
    """An overlap wider than the chunk would otherwise leave no room for new text."""
    chunks = split_text_chunks(_numbered_lines(), chunk_size=120, overlap=500)
    assert len(chunks) > 1
    for prev, nxt in zip(chunks, chunks[1:]):
        assert nxt.startswith(prev[-60:].lstrip())


def test_overlap_does_not_duplicate_a_whole_chunk():
    chunks = split_text_chunks(_numbered_lines(), chunk_size=200, overlap=40)
    assert len(set(chunks)) == len(chunks)
