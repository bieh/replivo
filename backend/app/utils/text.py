import tiktoken


def count_tokens(text: str, model: str = 'gpt-4') -> int:
    """Count tokens using tiktoken."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding('cl100k_base')
    return len(enc.encode(text))


def clean_text(text: str) -> str:
    """Clean extracted PDF text."""
    import re
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
