"""Cohere rerank integration."""
import cohere
from ..config import Config

co = cohere.Client(api_key=Config.COHERE_API_KEY)


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
