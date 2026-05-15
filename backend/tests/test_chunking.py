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
