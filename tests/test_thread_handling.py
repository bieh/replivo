"""Tests for conversation thread handling (follow-ups)."""
import pytest
from unittest.mock import patch, MagicMock

from backend.app.models import Conversation, Message
from backend.app.services.ai_service import _build_history_block
from backend.app.services.pipeline import (
    process_inbound_email, process_question, _build_conversation_history,
)


# ---------------------------------------------------------------------------
# Unit tests: _build_history_block
# ---------------------------------------------------------------------------

class TestBuildHistoryBlock:
    def test_returns_empty_when_none(self):
        assert _build_history_block(None) == ""

    def test_returns_empty_when_empty_list(self):
        assert _build_history_block([]) == ""

    def test_single_tenant_message(self):
        history = [{"role": "tenant", "text": "Can I paint?"}]
        result = _build_history_block(history)
        assert "Previous conversation:" in result
        assert 'Tenant: "Can I paint?"' in result

    def test_tenant_and_replivo(self):
        history = [
            {"role": "tenant", "text": "Can I paint?"},
            {"role": "replivo", "text": "Yes per Section 7.6"},
        ]
        result = _build_history_block(history)
        assert 'Tenant: "Can I paint?"' in result
        assert 'Replivo: "Yes per Section 7.6"' in result

    def test_multi_turn(self):
        history = [
            {"role": "tenant", "text": "Q1"},
            {"role": "replivo", "text": "A1"},
            {"role": "tenant", "text": "Q2"},
            {"role": "replivo", "text": "A2"},
        ]
        result = _build_history_block(history)
        assert result.count("Tenant:") == 2
        assert result.count("Replivo:") == 2


# ---------------------------------------------------------------------------
# Unit tests: _build_conversation_history
# ---------------------------------------------------------------------------

class TestBuildConversationHistory:
    def test_builds_history_from_messages(self, app, db, seed_data):
        conv = Conversation(
            community_id='comm-1', tenant_id='tenant-1',
            subject='Paint', status='draft_ready',
            sender_email='alice@example.com',
        )
        db.session.add(conv)
        db.session.flush()

        m1 = Message(
            conversation_id=conv.id, direction='inbound',
            from_email='alice@example.com', to_email='test@replivo.example.com',
            body_text='Can I paint my house?',
        )
        m2 = Message(
            conversation_id=conv.id, direction='outbound',
            from_email='test@replivo.example.com', to_email='alice@example.com',
            body_text='Yes per Section 7.6', is_ai_generated=True,
        )
        db.session.add_all([m1, m2])
        db.session.commit()

        history = _build_conversation_history(conv)
        assert len(history) == 2
        assert history[0] == {'role': 'tenant', 'text': 'Can I paint my house?'}
        assert history[1] == {'role': 'replivo', 'text': 'Yes per Section 7.6'}

    def test_empty_conversation(self, app, db, seed_data):
        conv = Conversation(
            community_id='comm-1', tenant_id='tenant-1',
            subject='Empty', status='pending_review',
            sender_email='alice@example.com',
        )
        db.session.add(conv)
        db.session.commit()

        history = _build_conversation_history(conv)
        assert history == []

    def test_skips_outbound_without_body(self, app, db, seed_data):
        conv = Conversation(
            community_id='comm-1', tenant_id='tenant-1',
            subject='Test', status='draft_ready',
            sender_email='alice@example.com',
        )
        db.session.add(conv)
        db.session.flush()

        m1 = Message(
            conversation_id=conv.id, direction='inbound',
            from_email='alice@example.com', to_email='test@replivo.example.com',
            body_text='Hello',
        )
        m2 = Message(
            conversation_id=conv.id, direction='outbound',
            from_email='test@replivo.example.com', to_email='alice@example.com',
            body_text='', is_ai_generated=True,
        )
        db.session.add_all([m1, m2])
        db.session.commit()

        history = _build_conversation_history(conv)
        assert len(history) == 1
        assert history[0]['role'] == 'tenant'


# ---------------------------------------------------------------------------
# Integration tests: process_question with conversation_history
# ---------------------------------------------------------------------------

MOCK_LLM_RESPONSE = {
    'reasoning': 'test reasoning',
    'answer_type': 'DEFINITIVE',
    'claims': [],
    'answer_text': 'Test answer',
    'overall_confidence': 'HIGH',
    'answer_completeness': 'FULL',
    'unanswered_parts': '',
    'should_escalate': False,
    'escalation_reason': '',
    'sections_reviewed': [],
}


class TestProcessQuestionWithHistory:
    @patch('backend.app.services.pipeline.get_context_for_community')
    @patch('backend.app.services.pipeline.generate_response')
    def test_history_passed_to_generate_response(self, mock_gen, mock_ctx, app, db, seed_data):
        mock_ctx.return_value = {
            'mode': 'full_context',
            'context_text': 'Some doc text',
            'total_tokens': 100,
        }
        mock_gen.return_value = MOCK_LLM_RESPONSE

        history = [
            {'role': 'tenant', 'text': 'Can I paint?'},
            {'role': 'replivo', 'text': 'Yes per Section 7.6'},
        ]

        result = process_question('comm-1', 'What colors?',
                                  conversation_history=history)

        assert result['status'] == 'draft_ready'
        # Verify history was forwarded to generate_response
        _, kwargs = mock_gen.call_args
        assert kwargs['conversation_history'] == history

    @patch('backend.app.services.pipeline.get_context_for_community')
    @patch('backend.app.services.pipeline.generate_response')
    def test_no_history_by_default(self, mock_gen, mock_ctx, app, db, seed_data):
        mock_ctx.return_value = {
            'mode': 'full_context',
            'context_text': 'Some doc text',
            'total_tokens': 100,
        }
        mock_gen.return_value = MOCK_LLM_RESPONSE

        result = process_question('comm-1', 'Can I paint?')

        assert result['status'] == 'draft_ready'
        _, kwargs = mock_gen.call_args
        assert kwargs['conversation_history'] is None


# ---------------------------------------------------------------------------
# Integration tests: process_inbound_email thread matching
# ---------------------------------------------------------------------------

class TestProcessInboundEmailThreading:
    @patch('backend.app.services.pipeline.process_question')
    def test_new_thread_creates_conversation(self, mock_pq, app, db, seed_data):
        mock_pq.return_value = {
            'status': 'draft_ready',
            'answer_text': 'First answer',
            'citations': [],
            'escalation_reason': '',
            'raw_response': MOCK_LLM_RESPONSE,
        }

        result = process_inbound_email({
            'from': 'alice@example.com',
            'to': 'test@replivo.example.com',
            'subject': 'Paint question',
            'body': 'Can I paint?',
            'thread_id': 'thread-abc',
            'message_id': 'msg-1',
        })

        assert result['status'] == 'draft_ready'
        conv = Conversation.query.get(result['conversation_id'])
        assert conv is not None
        assert conv.agentmail_thread_id == 'thread-abc'
        assert conv.messages.count() == 2  # inbound + AI draft

    @patch('backend.app.services.pipeline.process_question')
    def test_followup_appends_to_existing_conversation(self, mock_pq, app, db, seed_data):
        mock_pq.return_value = {
            'status': 'draft_ready',
            'answer_text': 'Answer text',
            'citations': [],
            'escalation_reason': '',
            'raw_response': MOCK_LLM_RESPONSE,
        }

        # First email creates conversation
        result1 = process_inbound_email({
            'from': 'alice@example.com',
            'to': 'test@replivo.example.com',
            'subject': 'Paint question',
            'body': 'Can I paint?',
            'thread_id': 'thread-xyz',
            'message_id': 'msg-1',
        })
        conv_id = result1['conversation_id']

        # Second email on same thread
        result2 = process_inbound_email({
            'from': 'alice@example.com',
            'to': 'test@replivo.example.com',
            'subject': 'Re: Paint question',
            'body': 'What colors?',
            'thread_id': 'thread-xyz',
            'message_id': 'msg-2',
        })

        # Should reuse the same conversation
        assert result2['conversation_id'] == conv_id

        conv = Conversation.query.get(conv_id)
        # 2 inbound + 2 AI drafts = 4
        assert conv.messages.count() == 4

    @patch('backend.app.services.pipeline.process_question')
    def test_followup_passes_history(self, mock_pq, app, db, seed_data):
        mock_pq.return_value = {
            'status': 'draft_ready',
            'answer_text': 'Answer',
            'citations': [],
            'escalation_reason': '',
            'raw_response': MOCK_LLM_RESPONSE,
        }

        # First email
        process_inbound_email({
            'from': 'alice@example.com',
            'to': 'test@replivo.example.com',
            'subject': 'Q1',
            'body': 'Can I paint?',
            'thread_id': 'thread-hist',
            'message_id': 'msg-1',
        })

        # Second email — should pass conversation_history
        process_inbound_email({
            'from': 'alice@example.com',
            'to': 'test@replivo.example.com',
            'subject': 'Re: Q1',
            'body': 'What colors?',
            'thread_id': 'thread-hist',
            'message_id': 'msg-2',
        })

        # Second call should have conversation_history
        assert mock_pq.call_count == 2
        _, kwargs = mock_pq.call_args_list[1]
        history = kwargs.get('conversation_history')
        assert history is not None
        assert len(history) >= 2  # at least original Q + A

    @patch('backend.app.services.pipeline.process_question')
    def test_no_thread_id_always_creates_new(self, mock_pq, app, db, seed_data):
        mock_pq.return_value = {
            'status': 'draft_ready',
            'answer_text': 'Answer',
            'citations': [],
            'escalation_reason': '',
            'raw_response': MOCK_LLM_RESPONSE,
        }

        result1 = process_inbound_email({
            'from': 'alice@example.com',
            'to': 'test@replivo.example.com',
            'subject': 'Q1',
            'body': 'Question 1',
        })
        result2 = process_inbound_email({
            'from': 'alice@example.com',
            'to': 'test@replivo.example.com',
            'subject': 'Q2',
            'body': 'Question 2',
        })

        assert result1['conversation_id'] != result2['conversation_id']

    @patch('backend.app.services.pipeline.process_question')
    def test_unknown_sender_gets_ai_draft(self, mock_pq, app, db, seed_data):
        mock_pq.return_value = {
            'status': 'draft_ready',
            'answer_text': 'AI answer for unknown sender',
            'citations': [],
            'escalation_reason': '',
            'raw_response': MOCK_LLM_RESPONSE,
        }

        result = process_inbound_email({
            'from': 'stranger@example.com',
            'to': 'test@replivo.example.com',
            'subject': 'Question from stranger',
            'body': 'Can I have a dog?',
            'message_id': 'msg-stranger',
        })

        assert result['status'] == 'draft_ready'
        assert result['answer_text'] == 'AI answer for unknown sender'
        conv = Conversation.query.get(result['conversation_id'])
        assert conv is not None
        assert conv.tenant_id is None
        assert conv.messages.count() == 2  # inbound + AI draft

    @patch('backend.app.services.pipeline.process_question')
    def test_followup_reopens_conversation(self, mock_pq, app, db, seed_data):
        mock_pq.return_value = {
            'status': 'draft_ready',
            'answer_text': 'Answer',
            'citations': [],
            'escalation_reason': '',
            'raw_response': MOCK_LLM_RESPONSE,
        }

        # Create and close a conversation
        result1 = process_inbound_email({
            'from': 'alice@example.com',
            'to': 'test@replivo.example.com',
            'subject': 'Q1',
            'body': 'Can I paint?',
            'thread_id': 'thread-reopen',
            'message_id': 'msg-1',
        })
        conv = Conversation.query.get(result1['conversation_id'])
        conv.status = 'closed'
        db.session.commit()

        # Follow-up arrives — should reopen
        result2 = process_inbound_email({
            'from': 'alice@example.com',
            'to': 'test@replivo.example.com',
            'subject': 'Re: Q1',
            'body': 'What about blue?',
            'thread_id': 'thread-reopen',
            'message_id': 'msg-2',
        })

        assert result2['conversation_id'] == conv.id
        conv = Conversation.query.get(conv.id)
        # Status should be updated from pipeline result, not still 'closed'
        assert conv.status == 'draft_ready'


# ---------------------------------------------------------------------------
# Integration tests: Playground endpoint with conversation_history
# ---------------------------------------------------------------------------

class TestPlaygroundEndpoint:
    def _login(self, client, db, seed_data):
        """Helper to authenticate the test client."""
        client.post('/api/auth/login', json={
            'username': 'admin', 'password': 'password',
        })

    @patch('backend.app.services.pipeline.process_question')
    def test_accepts_conversation_history(self, mock_pq, client, db, seed_data):
        mock_pq.return_value = {
            'status': 'draft_ready',
            'answer_text': 'Follow-up answer',
            'citations': [],
            'escalation_reason': '',
            'raw_response': MOCK_LLM_RESPONSE,
        }

        self._login(client, db, seed_data)

        history = [
            {'role': 'tenant', 'text': 'Can I paint?'},
            {'role': 'replivo', 'text': 'Yes per Section 7.6'},
        ]

        resp = client.post('/api/playground/ask', json={
            'community_id': 'comm-1',
            'question': 'What colors?',
            'conversation_history': history,
        })

        assert resp.status_code == 200
        _, kwargs = mock_pq.call_args
        assert kwargs['conversation_history'] == history

    @patch('backend.app.services.pipeline.process_question')
    def test_works_without_history(self, mock_pq, client, db, seed_data):
        mock_pq.return_value = {
            'status': 'draft_ready',
            'answer_text': 'Answer',
            'citations': [],
            'escalation_reason': '',
            'raw_response': MOCK_LLM_RESPONSE,
        }

        self._login(client, db, seed_data)

        resp = client.post('/api/playground/ask', json={
            'community_id': 'comm-1',
            'question': 'Can I paint?',
        })

        assert resp.status_code == 200
        _, kwargs = mock_pq.call_args
        assert kwargs.get('conversation_history') is None


# ---------------------------------------------------------------------------
# Integration tests: generate_response / verify_response with history
# ---------------------------------------------------------------------------

class TestAIServiceHistory:
    @patch('backend.app.services.ai_service.client')
    def test_generate_response_includes_history(self, mock_openai):
        from backend.app.services.ai_service import generate_response

        mock_choice = MagicMock()
        mock_choice.message.content = '{"reasoning":"r","answer_type":"DEFINITIVE","claims":[],"answer_text":"a","overall_confidence":"HIGH","answer_completeness":"FULL","unanswered_parts":"","should_escalate":false,"escalation_reason":"","sections_reviewed":[]}'
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )

        history = [
            {'role': 'tenant', 'text': 'Can I paint?'},
            {'role': 'replivo', 'text': 'Yes'},
        ]

        generate_response(
            question='What colors?',
            context_text='Doc text',
            context_mode='full_context',
            conversation_history=history,
        )

        call_args = mock_openai.chat.completions.create.call_args
        user_msg = call_args[1]['messages'][1]['content']
        assert 'Previous conversation:' in user_msg
        assert 'Can I paint?' in user_msg
        assert 'What colors?' in user_msg

    @patch('backend.app.services.ai_service.client')
    def test_generate_response_no_history_block_when_none(self, mock_openai):
        from backend.app.services.ai_service import generate_response

        mock_choice = MagicMock()
        mock_choice.message.content = '{"reasoning":"r","answer_type":"DEFINITIVE","claims":[],"answer_text":"a","overall_confidence":"HIGH","answer_completeness":"FULL","unanswered_parts":"","should_escalate":false,"escalation_reason":"","sections_reviewed":[]}'
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )

        generate_response(
            question='Can I paint?',
            context_text='Doc text',
            context_mode='full_context',
        )

        call_args = mock_openai.chat.completions.create.call_args
        user_msg = call_args[1]['messages'][1]['content']
        assert 'Previous conversation:' not in user_msg

    @patch('backend.app.services.ai_service.client')
    def test_verify_response_includes_history(self, mock_openai):
        from backend.app.services.ai_service import verify_response

        mock_choice = MagicMock()
        mock_choice.message.content = '{"reasoning":"r","answer_type":"DEFINITIVE","claims":[],"answer_text":"a","overall_confidence":"HIGH","answer_completeness":"FULL","unanswered_parts":"","should_escalate":false,"escalation_reason":"","sections_reviewed":[]}'
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )

        history = [{'role': 'tenant', 'text': 'Prior Q'}]

        verify_response(
            question='Follow up?',
            initial_response=MOCK_LLM_RESPONSE,
            context_text='Doc text',
            flagged_claims=[],
            conversation_history=history,
        )

        call_args = mock_openai.chat.completions.create.call_args
        user_msg = call_args[1]['messages'][1]['content']
        assert 'Previous conversation:' in user_msg
        assert 'Prior Q' in user_msg
