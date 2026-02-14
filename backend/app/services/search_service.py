"""Hybrid search: pgvector similarity + PostgreSQL BM25 + Reciprocal Rank Fusion."""
from sqlalchemy import text
from ..extensions import db
from ..models import Document, DocumentChunk
from ..utils.text import count_tokens
from .embedding_service import generate_embedding
from .rerank_service import rerank_chunks

# HOA synonym mapping for query expansion (rule-based, no LLM)
SYNONYM_MAP = {
    'pet': ['animal', 'dog', 'cat', 'pets', 'animals'],
    'dog': ['pet', 'animal', 'dogs', 'canine'],
    'cat': ['pet', 'animal', 'cats', 'feline'],
    'fence': ['fencing', 'wall', 'boundary', 'perimeter'],
    'paint': ['color', 'exterior', 'painting', 'colours'],
    'color': ['paint', 'colour', 'colors', 'exterior'],
    'rent': ['rental', 'lease', 'sublease', 'airbnb', 'short-term'],
    'airbnb': ['rental', 'short-term', 'transient', 'lease'],
    'park': ['parking', 'vehicle', 'car', 'garage', 'driveway'],
    'parking': ['park', 'vehicle', 'car', 'garage', 'driveway'],
    'rv': ['recreational vehicle', 'camper', 'trailer', 'motorhome'],
    'tree': ['trees', 'vegetation', 'landscaping', 'removal'],
    'noise': ['quiet', 'nuisance', 'disturbance', 'sound'],
    'grill': ['barbecue', 'bbq', 'charcoal', 'cooking'],
    'sign': ['signs', 'signage', 'display'],
    'satellite': ['dish', 'antenna', 'satellite dish'],
    'pool': ['swimming', 'swimming pool', 'recreation'],
    'dues': ['assessment', 'fee', 'fees', 'charges', 'monthly'],
    'assessment': ['dues', 'fee', 'fees', 'charges'],
    'renovate': ['remodel', 'improvement', 'modification', 'alteration', 'renovation'],
    'chicken': ['poultry', 'barnyard', 'livestock', 'chickens'],
    'horse': ['horses', 'equine', 'livestock', 'equestrian'],
    'business': ['commercial', 'home occupation', 'home business', 'work'],
    'alcohol': ['liquor', 'beer', 'wine', 'drinking'],
    'boat': ['watercraft', 'vessel', 'trailer'],
    'laundry': ['clothes', 'drying', 'clothesline', 'washing'],
    'floor': ['flooring', 'carpet', 'hardwood', 'tile'],
    'window': ['windows', 'window covering', 'curtain', 'blinds'],
    'solar': ['solar panel', 'photovoltaic', 'energy'],
    'garage': ['garage door', 'parking', 'carport'],
    'height': ['tall', 'maximum height', 'feet'],
    'size': ['square feet', 'minimum', 'square footage', 'area'],
}


def expand_query(query: str) -> str:
    """Expand query with HOA-specific synonyms (rule-based, no LLM)."""
    words = query.lower().split()
    expanded_terms = set(words)
    for word in words:
        if word in SYNONYM_MAP:
            expanded_terms.update(SYNONYM_MAP[word])
    return ' '.join(expanded_terms)


def get_context_for_community(community_id: str, question: str) -> dict:
    """Determine context strategy and retrieve relevant document content.

    Returns:
        {
            'mode': 'full_context' | 'rag',
            'context_text': str,
            'chunks': list[dict],  # for RAG mode
            'total_tokens': int,
        }
    """
    # Get all documents for this community
    docs = Document.query.filter_by(community_id=community_id, status='ready').all()
    if not docs:
        return {
            'mode': 'no_documents',
            'context_text': '',
            'chunks': [],
            'total_tokens': 0,
        }

    # Calculate total tokens
    total_tokens = sum(d.total_tokens for d in docs)

    # Full context mode if total <= 80K tokens
    if total_tokens <= 80000:
        full_text = '\n\n---\n\n'.join(d.full_text for d in docs if d.full_text)
        return {
            'mode': 'full_context',
            'context_text': full_text,
            'chunks': [],
            'total_tokens': total_tokens,
        }

    # RAG mode
    chunks = hybrid_search(community_id, question, top_n=15)
    reranked = rerank_chunks(question, chunks, top_n=8)

    # Order by document position (chunk_index) for logical flow
    reranked.sort(key=lambda c: (c.get('document_id', ''), c.get('chunk_index', 0)))

    # Assemble context text
    context_parts = []
    for c in reranked:
        header = ''
        if c.get('section_number'):
            header = f"[{c['section_number']}]"
        elif c.get('article_number'):
            header = f"[{c['article_number']}]"
        context_parts.append(f"{header}\n{c['content']}")

    context_text = '\n\n---\n\n'.join(context_parts)

    return {
        'mode': 'rag',
        'context_text': context_text,
        'chunks': reranked,
        'total_tokens': count_tokens(context_text),
    }


def hybrid_search(community_id: str, query: str, top_n: int = 15) -> list[dict]:
    """Hybrid search: vector similarity + BM25 full-text, merged with RRF."""
    expanded = expand_query(query)

    # Vector search
    query_embedding = generate_embedding(expanded)
    vector_results = _vector_search(community_id, query_embedding, limit=top_n * 2)

    # BM25 search
    bm25_results = _bm25_search(community_id, expanded, limit=top_n * 2)

    # Reciprocal Rank Fusion
    fused = _reciprocal_rank_fusion(vector_results, bm25_results, k=60)

    return fused[:top_n]


def _vector_search(community_id: str, embedding: list[float], limit: int = 30) -> list[dict]:
    """Cosine similarity search via pgvector."""
    # Get document IDs for this community
    doc_ids = [d.id for d in Document.query.filter_by(community_id=community_id, status='ready').all()]
    if not doc_ids:
        return []

    embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'

    results = db.session.execute(
        text("""
            SELECT id, document_id, chunk_index, content, article_number, article_title,
                   section_group, section_number, page_number, token_count,
                   1 - (embedding <=> :embedding::vector) as similarity
            FROM document_chunks
            WHERE document_id = ANY(:doc_ids)
            AND embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """),
        {'embedding': embedding_str, 'doc_ids': doc_ids, 'limit': limit}
    ).fetchall()

    return [
        {
            'id': r.id,
            'document_id': r.document_id,
            'chunk_index': r.chunk_index,
            'content': r.content,
            'article_number': r.article_number,
            'article_title': r.article_title,
            'section_group': r.section_group,
            'section_number': r.section_number,
            'page_number': r.page_number,
            'token_count': r.token_count,
            'score': float(r.similarity),
        }
        for r in results
    ]


def _bm25_search(community_id: str, query: str, limit: int = 30) -> list[dict]:
    """PostgreSQL full-text search using tsvector."""
    doc_ids = [d.id for d in Document.query.filter_by(community_id=community_id, status='ready').all()]
    if not doc_ids:
        return []

    # Convert query to tsquery format
    words = query.split()
    tsquery = ' | '.join(words)

    results = db.session.execute(
        text("""
            SELECT id, document_id, chunk_index, content, article_number, article_title,
                   section_group, section_number, page_number, token_count,
                   ts_rank(search_vector, to_tsquery('english', :query)) as rank
            FROM document_chunks
            WHERE document_id = ANY(:doc_ids)
            AND search_vector IS NOT NULL
            AND search_vector @@ to_tsquery('english', :query)
            ORDER BY rank DESC
            LIMIT :limit
        """),
        {'query': tsquery, 'doc_ids': doc_ids, 'limit': limit}
    ).fetchall()

    return [
        {
            'id': r.id,
            'document_id': r.document_id,
            'chunk_index': r.chunk_index,
            'content': r.content,
            'article_number': r.article_number,
            'article_title': r.article_title,
            'section_group': r.section_group,
            'section_number': r.section_number,
            'page_number': r.page_number,
            'token_count': r.token_count,
            'score': float(r.rank),
        }
        for r in results
    ]


def _reciprocal_rank_fusion(list_a: list[dict], list_b: list[dict], k: int = 60) -> list[dict]:
    """Merge two ranked lists using Reciprocal Rank Fusion."""
    scores = {}
    chunks_by_id = {}

    for rank, item in enumerate(list_a):
        cid = item['id']
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        chunks_by_id[cid] = item

    for rank, item in enumerate(list_b):
        cid = item['id']
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        chunks_by_id[cid] = item

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    result = []
    for cid in sorted_ids:
        chunk = chunks_by_id[cid]
        chunk['rrf_score'] = scores[cid]
        result.append(chunk)

    return result
