"""LLM calls with structured output for draft generation and verification."""
import json
from openai import OpenAI
from ..config import Config

client = OpenAI(api_key=Config.OPENAI_API_KEY)

import os
MODEL = os.getenv('OPENAI_MODEL', 'gpt-5.2')

SYSTEM_PROMPT = """You are an AI assistant for a property management company. Your job is to answer tenant questions by citing their community's governing documents (CC&Rs, bylaws, rules).

CRITICAL RULES — FOLLOW THESE EXACTLY:

1. ONLY state facts that are EXPLICITLY written in the provided documents. Never infer, guess, or use outside knowledge.

2. Every factual claim MUST include:
   - The EXACT quote from the document (source_quote)
   - The specific section/article reference (section_reference)
   - Your confidence level (HIGH/MEDIUM/LOW)

3. If the answer is NOT in the documents:
   - Set answer_type to "NOT_IN_DOCUMENTS"
   - Set should_escalate to true
   - Say "This topic is not addressed in the community's governing documents. I'm forwarding your question to your property manager."
   - Do NOT make up rules, hours, amounts, or policies

4. NEVER say "since it's not mentioned, it must be allowed" — that is WRONG. Absence of a rule does NOT mean permission. Say it's not addressed.

5. If the answer is ambiguous or requires interpretation:
   - Set answer_type to "AMBIGUOUS" or "REQUIRES_INTERPRETATION"
   - Set should_escalate to true
   - Present what the documents DO say, then note the ambiguity

6. For the answer_text: write a professional, friendly email response. Include inline citations like "(Section 7.6)" after relevant statements. Address the tenant directly.

7. Think step-by-step in the "reasoning" field before answering. This helps you avoid mistakes.

8. Be precise about numbers, dates, and requirements. Quote them exactly.
"""

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "ccr_response",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Step-by-step thinking about the question and what the documents say. Not shown to tenant."
                },
                "answer_type": {
                    "type": "string",
                    "enum": ["DEFINITIVE", "PARTIAL", "NOT_IN_DOCUMENTS", "AMBIGUOUS", "REQUIRES_INTERPRETATION"]
                },
                "claims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim_text": {"type": "string", "description": "The factual statement"},
                            "section_reference": {"type": "string", "description": "e.g. 'Section 7.6' or 'Article VIII.I'"},
                            "source_quote": {"type": "string", "description": "EXACT text from the document"},
                            "confidence": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]}
                        },
                        "required": ["claim_text", "section_reference", "source_quote", "confidence"],
                        "additionalProperties": False
                    }
                },
                "answer_text": {
                    "type": "string",
                    "description": "The readable email response with inline citations"
                },
                "overall_confidence": {
                    "type": "string",
                    "enum": ["HIGH", "MEDIUM", "LOW"]
                },
                "answer_completeness": {
                    "type": "string",
                    "enum": ["FULL", "PARTIAL", "NONE"]
                },
                "unanswered_parts": {
                    "type": "string",
                    "description": "What parts of the question the documents don't cover"
                },
                "should_escalate": {"type": "boolean"},
                "escalation_reason": {
                    "type": "string",
                    "description": "Why this should be escalated (empty if not escalating)"
                },
                "sections_reviewed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "All section/article references examined"
                }
            },
            "required": [
                "reasoning", "answer_type", "claims", "answer_text",
                "overall_confidence", "answer_completeness", "unanswered_parts",
                "should_escalate", "escalation_reason", "sections_reviewed"
            ],
            "additionalProperties": False
        }
    }
}


def _build_history_block(conversation_history: list[dict] | None) -> str:
    """Build a text block summarizing prior conversation turns."""
    if not conversation_history:
        return ""
    lines = []
    for entry in conversation_history:
        role = entry.get("role", "unknown").capitalize()
        text = entry.get("text", "")
        label = "Tenant" if role.lower() == "tenant" else "Replivo"
        lines.append(f'{label}: "{text}"')
    return "Previous conversation:\n---\n" + "\n".join(lines) + "\n---\n\n"


def generate_response(question: str, context_text: str, context_mode: str,
                      tenant_name: str = None,
                      conversation_history: list[dict] = None) -> dict:
    """LLM Call #1: Generate structured response with citations.

    Args:
        question: The tenant's question
        context_text: Document text (full or RAG chunks)
        context_mode: 'full_context' or 'rag'
        tenant_name: Optional tenant name for personalized response
        conversation_history: Optional list of prior messages [{role, text}, ...]

    Returns:
        Parsed JSON response matching RESPONSE_SCHEMA
    """
    greeting = f"The tenant's name is {tenant_name}. " if tenant_name else ""
    history_block = _build_history_block(conversation_history)

    user_message = f"""{greeting}{history_block}The tenant asks:

"{question}"

Here are the community's governing documents:

{context_text}

Answer the tenant's question using ONLY information from these documents. Follow all rules in your system prompt."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format=RESPONSE_SCHEMA,
        temperature=0.1,
    )

    return json.loads(response.choices[0].message.content)


VERIFY_SYSTEM_PROMPT = """You are a verification assistant. You are given:
1. A tenant's question
2. An AI-generated response with claims and citations
3. The actual source document text

Your job: verify each claim against the source text. For each claim:
- Check if the source_quote actually exists in the documents
- Check if the claim_text accurately represents what the document says
- Check if the section_reference is correct

If any claim is unsupported, remove it or fix it. If the overall answer becomes unreliable after removing unsupported claims, set should_escalate to true.

Be conservative: if in doubt, escalate rather than approve a potentially wrong answer.
"""


def verify_response(question: str, initial_response: dict, context_text: str,
                    flagged_claims: list[dict],
                    conversation_history: list[dict] = None) -> dict:
    """LLM Call #2: Verify flagged claims against source text.

    Only called when initial response has unverified citations, MEDIUM confidence, or PARTIAL answer.

    Args:
        question: Original question
        initial_response: The response from Call #1
        context_text: Source document text
        flagged_claims: Claims that failed citation verification
        conversation_history: Optional list of prior messages [{role, text}, ...]

    Returns:
        Updated response dict
    """
    flagged_info = json.dumps(flagged_claims, indent=2)
    history_block = _build_history_block(conversation_history)

    user_message = f"""{history_block}Original question: "{question}"

AI Response to verify:
{json.dumps(initial_response, indent=2)}

FLAGGED CLAIMS (these citations could not be verified in the source text):
{flagged_info}

Source documents:
{context_text}

Please re-verify the response. Remove any unsupported claims, fix any incorrect citations, and update confidence levels. If the answer is no longer reliable after corrections, set should_escalate to true."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": VERIFY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format=RESPONSE_SCHEMA,
        temperature=0.0,
    )

    return json.loads(response.choices[0].message.content)
