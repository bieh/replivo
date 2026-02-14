"""OpenAI embedding generation with batching and retry."""
import time
from openai import OpenAI
from ..config import Config

client = OpenAI(api_key=Config.OPENAI_API_KEY)

EMBEDDING_MODEL = 'text-embedding-3-small'
BATCH_SIZE = 100  # OpenAI allows up to 2048 in a single call
MAX_RETRIES = 3


def generate_embedding(text: str) -> list[float]:
    """Generate embedding for a single text."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts, with batching and retry."""
    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        embeddings = _embed_with_retry(batch)
        all_embeddings.extend(embeddings)

    return all_embeddings


def _embed_with_retry(texts: list[str]) -> list[list[float]]:
    """Call OpenAI embeddings API with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
            )
            return [d.embedding for d in response.data]
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"  Embedding API error (retry {attempt + 1}): {e}, waiting {wait}s")
                time.sleep(wait)
            else:
                raise
