"""Deterministic citation verification — no LLM needed.

For each claim's source_quote, fuzzy-match against actual document text.
Flags any unverified citations.
"""
from thefuzz import fuzz


def verify_citations(claims: list[dict], document_text: str, threshold: int = 75) -> list[dict]:
    """Verify each claim's source_quote exists in the document text.

    Args:
        claims: List of claim dicts with 'source_quote' field
        document_text: The full document text to match against
        threshold: Minimum fuzzy match score (0-100) to consider verified

    Returns:
        List of claims with added 'citation_verified' and 'match_score' fields
    """
    if not document_text:
        for claim in claims:
            claim['citation_verified'] = False
            claim['match_score'] = 0
        return claims

    doc_lower = document_text.lower()

    for claim in claims:
        quote = claim.get('source_quote', '')
        if not quote or len(quote.strip()) < 10:
            claim['citation_verified'] = False
            claim['match_score'] = 0
            continue

        quote_lower = quote.lower().strip()

        # First try exact substring match
        if quote_lower in doc_lower:
            claim['citation_verified'] = True
            claim['match_score'] = 100
            continue

        # Fuzzy match: slide a window of similar length over the doc
        best_score = _sliding_window_match(quote_lower, doc_lower)
        claim['citation_verified'] = best_score >= threshold
        claim['match_score'] = best_score

    return claims


def _sliding_window_match(quote: str, document: str) -> int:
    """Find the best fuzzy match score by sliding over the document."""
    quote_len = len(quote)
    if quote_len == 0:
        return 0

    best_score = 0
    # Use a step size proportional to quote length for efficiency
    step = max(1, quote_len // 4)
    window_size = int(quote_len * 1.3)  # slightly larger window

    for i in range(0, len(document) - quote_len + 1, step):
        window = document[i:i + window_size]
        score = fuzz.ratio(quote, window)
        if score > best_score:
            best_score = score
            if score >= 90:
                return score  # Early exit on good match

    return best_score


def has_unverified_citations(claims: list[dict]) -> bool:
    """Check if any claims have unverified citations."""
    return any(not c.get('citation_verified', True) for c in claims)
