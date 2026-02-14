"""Cohere rerank integration (optional — falls back to truncation if no API key)."""
from ..config import Config

_co = None


def _get_client():
    global _co
    if _co is None:
        if not Config.COHERE_API_KEY:
            return None
        import cohere
        _co = cohere.Client(api_key=Config.COHERE_API_KEY)
    return _co


def rerank_chunks(query: str, chunks: list[dict], top_n: int = 8) -> list[dict]:
    """Rerank chunks using Cohere rerank-english-v3.0.

    Args:
        query: The search query
        chunks: List of dicts with 'content' key
        top_n: Number of top results to return

    Returns:
        Reranked list of chunks (top_n items)
    """
    if not chunks:
        return []

    if len(chunks) <= top_n:
        return chunks

    co = _get_client()
    if co is None:
        return chunks[:top_n]

    try:
        response = co.rerank(
            model='rerank-english-v3.0',
            query=query,
            documents=[c['content'] for c in chunks],
            top_n=top_n,
        )
        reranked = []
        for result in response.results:
            chunk = chunks[result.index]
            chunk['rerank_score'] = result.relevance_score
            reranked.append(chunk)
        return reranked
    except Exception as e:
        print(f"  Rerank error: {e}, falling back to original order")
        return chunks[:top_n]
