from flask import Blueprint, jsonify, url_for
from ..models import Message

bp = Blueprint('citations', __name__)


@bp.route('/<token>', methods=['GET'])
def get_citation(token):
    """Public endpoint — no auth required."""
    msg = Message.query.filter_by(citation_token=token).first()
    if not msg:
        return jsonify({'error': 'Citation not found'}), 404

    conv = msg.conversation
    community_name = conv.community.name if conv.community else ''
    community_id = conv.community_id

    # Enrich citations with index and download URL
    raw_citations = msg.citations or []
    enriched = []
    for i, cit in enumerate(raw_citations, start=1):
        entry = {
            'index': i,
            'claim_text': cit.get('claim_text', ''),
            'section_reference': cit.get('section_reference', ''),
            'source_quote': cit.get('source_quote', ''),
            'confidence': cit.get('confidence', ''),
            'verified': cit.get('verified', False),
            'document_name': cit.get('document_name', ''),
            'chunk_content': cit.get('chunk_content', ''),
            'page_number': cit.get('page_number'),
        }
        doc_id = cit.get('document_id')

        # Live re-enrichment for old citations missing document_id
        if not doc_id and community_id:
            from ..services.pipeline import _find_matching_chunk
            chunk, doc = _find_matching_chunk(
                community_id,
                cit.get('section_reference', ''),
                cit.get('source_quote', ''),
            )
            if doc:
                doc_id = doc.id
                entry['document_name'] = entry['document_name'] or doc.filename
                if chunk:
                    entry['chunk_content'] = entry['chunk_content'] or chunk.content
                    entry['page_number'] = entry['page_number'] or chunk.page_number

        entry['document_id'] = doc_id
        if doc_id:
            entry['download_url'] = f'/api/documents/{doc_id}/download'
            entry['view_url'] = f'/api/documents/{doc_id}/view'
        else:
            entry['download_url'] = None
            entry['view_url'] = None
        enriched.append(entry)

    return jsonify({
        'subject': conv.subject,
        'answer_text': msg.body_text,
        'citations': enriched,
        'community_name': community_name,
    })
