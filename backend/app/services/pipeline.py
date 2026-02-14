"""Pipeline orchestrator: retrieve → generate → verify → escalate → store."""
import re
import uuid
from datetime import datetime, timezone

from ..extensions import db
from ..models import Community, Tenant, Conversation, Message, Document
from .search_service import get_context_for_community
from .ai_service import generate_response, verify_response
from .citation_verifier import verify_citations, has_unverified_citations


def _parse_email(raw: str) -> str:
    """Extract bare email from 'Name <email>' format."""
    match = re.search(r'<([^>]+)>', raw)
    return match.group(1) if match else raw.strip()


def process_question(community_id: str, question: str, tenant_email: str = None,
                     conversation_history: list[dict] = None) -> dict:
    """Run the full AI pipeline on a question.

    Returns a dict with:
        status: 'draft_ready' | 'needs_human'
        answer_text: str
        citations: list[dict]
        escalation_reason: str
        raw_response: dict (full LLM output)
    """
    # Get community
    community = Community.query.get(community_id)
    if not community:
        return {'status': 'needs_human', 'answer_text': '', 'escalation_reason': 'Community not found',
                'citations': [], 'raw_response': {}}

    # Get document context
    context = get_context_for_community(community_id, question)

    if context['mode'] == 'no_documents':
        return {
            'status': 'needs_human',
            'answer_text': 'No documents have been uploaded for this community yet.',
            'escalation_reason': 'No documents available',
            'citations': [],
            'raw_response': {},
        }

    # Look up tenant name for personalized response
    tenant_name = None
    if tenant_email:
        tenant = Tenant.query.filter_by(community_id=community_id, email=tenant_email).first()
        if tenant:
            tenant_name = tenant.name

    print(f"  Context mode: {context['mode']} ({context['total_tokens']} tokens)")

    # ===== LLM Call #1: Generate =====
    print(f"  Generating response...")
    response = generate_response(
        question=question,
        context_text=context['context_text'],
        context_mode=context['mode'],
        tenant_name=tenant_name,
        conversation_history=conversation_history,
    )

    # ===== Deterministic Citation Verification =====
    # Get full document text for verification
    docs = Document.query.filter_by(community_id=community_id, status='ready').all()
    full_doc_text = '\n\n'.join(d.full_text for d in docs if d.full_text)

    claims = response.get('claims', [])
    if claims:
        print(f"  Verifying {len(claims)} citations...")
        claims = verify_citations(claims, full_doc_text)
        response['claims'] = claims

        unverified = [c for c in claims if not c.get('citation_verified', True)]
        if unverified:
            print(f"  {len(unverified)} unverified citations found")

    # ===== LLM Call #2: Verify (conditional) =====
    needs_verification = (
        has_unverified_citations(claims) or
        response.get('overall_confidence') == 'MEDIUM' or
        response.get('answer_type') == 'PARTIAL'
    )

    if needs_verification:
        print(f"  Running verification pass...")
        flagged = [c for c in claims if not c.get('citation_verified', True)]
        response = verify_response(
            question=question,
            initial_response=response,
            context_text=context['context_text'],
            flagged_claims=flagged,
            conversation_history=conversation_history,
        )
        # Re-verify citations after Call #2
        claims = response.get('claims', [])
        if claims:
            claims = verify_citations(claims, full_doc_text)
            response['claims'] = claims

    # ===== Escalation Gate (8 deterministic rules) =====
    status, escalation_reason = apply_escalation_rules(response)
    print(f"  Status: {status}")
    if escalation_reason:
        print(f"  Escalation: {escalation_reason}")

    # Build citations for storage
    citations = [
        {
            'claim_text': c.get('claim_text', ''),
            'section_reference': c.get('section_reference', ''),
            'source_quote': c.get('source_quote', ''),
            'confidence': c.get('confidence', ''),
            'verified': c.get('citation_verified', False),
        }
        for c in response.get('claims', [])
    ]

    return {
        'status': status,
        'answer_text': response.get('answer_text', ''),
        'citations': citations,
        'escalation_reason': escalation_reason,
        'raw_response': response,
    }


def apply_escalation_rules(response: dict) -> tuple[str, str]:
    """Apply 8 deterministic escalation rules. Any trigger = needs_human.

    Returns: (status, escalation_reason)
    """
    reasons = []

    # Rule 1: Model explicitly says should_escalate
    if response.get('should_escalate'):
        reasons.append(f"Model flagged: {response.get('escalation_reason', 'unspecified')}")

    # Rule 2: answer_type is NOT_IN_DOCUMENTS
    if response.get('answer_type') == 'NOT_IN_DOCUMENTS':
        reasons.append("Answer not found in documents")

    # Rule 3: overall_confidence is LOW
    if response.get('overall_confidence') == 'LOW':
        reasons.append("Low overall confidence")

    # Rule 4: answer_type is REQUIRES_INTERPRETATION
    if response.get('answer_type') == 'REQUIRES_INTERPRETATION':
        reasons.append("Requires interpretation")

    # Rule 5: Any claim has unverified citation
    claims = response.get('claims', [])
    if any(not c.get('citation_verified', True) for c in claims):
        reasons.append("Unverified citation(s) after verification pass")

    # Rule 6: Any individual claim has LOW confidence
    if any(c.get('confidence') == 'LOW' for c in claims):
        reasons.append("Claim with low confidence")

    # Rule 7: answer_type is AMBIGUOUS
    if response.get('answer_type') == 'AMBIGUOUS':
        reasons.append("Ambiguous answer")

    # Rule 8: Zero claims but answer exists
    answer_text = response.get('answer_text', '')
    if not claims and answer_text and len(answer_text) > 50:
        # Check if it's a "not in documents" type response (those are OK without claims)
        if response.get('answer_type') not in ('NOT_IN_DOCUMENTS',):
            reasons.append("No citations backing the answer")

    if reasons:
        return 'needs_human', '; '.join(reasons)
    return 'draft_ready', ''


def process_inbound_email(email_data: dict) -> dict:
    """Process an inbound email through the full pipeline.

    Called by both webhook handler and email poller.
    email_data should have: from, to, subject, body, and optionally message_id, thread_id
    """
    sender_email = _parse_email(email_data.get('from', ''))
    to_email = email_data.get('to', '')
    subject = email_data.get('subject', '')
    body = email_data.get('body', '')
    message_id = email_data.get('message_id')
    thread_id = email_data.get('thread_id')

    # Find tenant and community
    tenant = Tenant.query.filter_by(email=sender_email, is_active=True).first()

    if tenant:
        community = tenant.community
    else:
        # Unknown sender — find community by inbox email, fall back to first
        community = Community.query.filter_by(inbox_email=to_email).first()
        if not community:
            community = Community.query.first()
        if not community:
            return {'status': 'error', 'error': 'No community found'}

    # Check for existing conversation on this thread
    existing_conv = None
    if thread_id:
        existing_conv = Conversation.query.filter_by(
            agentmail_thread_id=thread_id
        ).first()

    if existing_conv:
        conv = existing_conv

        # Append new inbound message
        inbound_msg = Message(
            conversation_id=conv.id,
            agentmail_message_id=message_id,
            direction='inbound',
            from_email=sender_email,
            to_email=to_email,
            subject=subject,
            body_text=body,
        )
        db.session.add(inbound_msg)
        db.session.flush()

        # Build conversation history from existing messages
        conversation_history = _build_conversation_history(conv)

        # Run AI pipeline with history
        result = process_question(community.id, body, sender_email,
                                  conversation_history=conversation_history)
    else:
        # Create new conversation
        conv = Conversation(
            community_id=community.id,
            tenant_id=tenant.id if tenant else None,
            agentmail_thread_id=thread_id,
            subject=subject,
            status='pending_review',
            sender_email=sender_email,
        )
        db.session.add(conv)
        db.session.flush()

        # Store inbound message
        inbound_msg = Message(
            conversation_id=conv.id,
            agentmail_message_id=message_id,
            direction='inbound',
            from_email=sender_email,
            to_email=to_email,
            subject=subject,
            body_text=body,
        )
        db.session.add(inbound_msg)
        db.session.flush()

        # Run AI pipeline
        result = process_question(community.id, body, sender_email)

    # Store AI draft as outbound message
    draft_msg = Message(
        conversation_id=conv.id,
        direction='outbound',
        from_email=to_email,
        to_email=sender_email,
        subject=f"Re: {subject}",
        body_text=result['answer_text'],
        citations=result['citations'],
        ai_response_data=result['raw_response'],
        is_ai_generated=True,
    )
    db.session.add(draft_msg)

    conv.status = result['status']

    # Auto-reply logic
    settings = community.settings or {}
    auto_reply = settings.get('auto_reply_enabled', False)

    if auto_reply and result['status'] == 'draft_ready':
        try:
            from .email_service import send_reply
            from ..config import Config
            token = uuid.uuid4().hex[:12]
            draft_msg.citation_token = token
            citation_url = f"{Config.FRONTEND_URL.rstrip('/')}/citations/{token}"
            send_reply(conv, result['answer_text'], citation_url=citation_url)
            conv.status = 'auto_replied'
            draft_msg.sent_at = datetime.now(timezone.utc)
        except Exception as e:
            print(f"  Auto-reply failed: {e}, keeping as draft_ready")

    db.session.commit()

    return {
        'status': conv.status,
        'conversation_id': conv.id,
        'answer_text': result['answer_text'],
    }


def _build_conversation_history(conv: Conversation) -> list[dict]:
    """Build conversation history from existing messages for LLM context."""
    history = []
    messages = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at).all()
    for msg in messages:
        if msg.direction == 'inbound':
            history.append({'role': 'tenant', 'text': msg.body_text or ''})
        elif msg.direction == 'outbound' and msg.body_text:
            history.append({'role': 'replivo', 'text': msg.body_text})
    return history
