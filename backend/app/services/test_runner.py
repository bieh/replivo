"""Test runner for grounding test suite — validates AI accuracy and hallucination prevention."""
import sys
import time

from ..models import Community
from .pipeline import process_question


def run_tests(category: str = None, community: str = None, verbose: bool = False):
    """Run the grounding test suite."""
    sys.path.insert(0, '.')
    from tests.test_fixtures import (
        ANSWERABLE_QUESTIONS, UNANSWERABLE_QUESTIONS,
        CROSS_COMMUNITY_QUESTIONS, UNKNOWN_SENDER_QUESTIONS,
    )

    # Build test sets
    tests = []
    if not category or category == 'answerable':
        tests.extend([dict(category='answerable', **q) for q in ANSWERABLE_QUESTIONS])
    if not category or category == 'unanswerable':
        tests.extend([dict(category='unanswerable', **q) for q in UNANSWERABLE_QUESTIONS])
    if not category or category == 'cross_community':
        tests.extend([dict(category='cross_community', **q) for q in CROSS_COMMUNITY_QUESTIONS])
    if not category or category == 'unknown_sender':
        tests.extend([dict(category='unknown_sender', **q) for q in UNKNOWN_SENDER_QUESTIONS])

    # Filter by community
    if community:
        tests = [t for t in tests if t.get('community') == community]

    print(f"\nRunning {len(tests)} test cases...\n")

    results = {'answerable': [], 'unanswerable': [], 'cross_community': [], 'unknown_sender': []}
    total_pass = 0
    total_fail = 0

    for i, test in enumerate(tests):
        cat = test['category']
        q = test['question']
        comm = test.get('community')

        print(f"[{i+1}/{len(tests)}] [{cat}] [{comm or 'unknown'}] \"{q[:60]}\"")

        if cat == 'unknown_sender':
            # Unknown sender test — we check that the system flags it
            result = _run_unknown_sender_test(test, verbose)
        else:
            # Get community
            community_obj = Community.query.filter_by(slug=comm).first()
            if not community_obj:
                print(f"  SKIP: Community '{comm}' not found")
                continue

            try:
                start = time.time()
                response = process_question(community_obj.id, q, test.get('tenant_email'))
                elapsed = time.time() - start
                result = _evaluate_test(test, response, elapsed, verbose)
            except Exception as e:
                result = {'passed': False, 'reason': f'Exception: {e}'}
                print(f"  FAIL: {result['reason']}")

        if result['passed']:
            total_pass += 1
            print(f"  PASS{f' ({result.get(\"detail\", \"\")})' if result.get('detail') else ''}")
        else:
            total_fail += 1
            print(f"  FAIL: {result['reason']}")

        if verbose and 'response' in result:
            print(f"    Status: {result['response'].get('status')}")
            print(f"    Answer: {result['response'].get('answer_text', '')[:200]}")
            if result['response'].get('citations'):
                for c in result['response']['citations']:
                    print(f"    Citation: {c.get('section_reference', 'N/A')}")

        results[cat].append(result)
        print()

    # Summary
    print("=" * 70)
    print(f"RESULTS: {total_pass}/{total_pass + total_fail} passed ({100*total_pass/(total_pass+total_fail):.1f}%)")

    for cat in ['answerable', 'unanswerable', 'cross_community', 'unknown_sender']:
        cat_results = results[cat]
        if not cat_results:
            continue
        passed = sum(1 for r in cat_results if r['passed'])
        label = cat.replace('_', ' ').title()
        critical = " <-- CRITICAL: any failure here is a hallucination" if cat == 'unanswerable' else ""
        print(f"  {label}: {passed}/{len(cat_results)} ({100*passed/len(cat_results):.1f}%){critical}")

    print()


def _evaluate_test(test: dict, response: dict, elapsed: float, verbose: bool) -> dict:
    """Evaluate a single test case against the AI response."""
    cat = test['category']
    result = {'response': response, 'elapsed': elapsed}

    if cat == 'answerable':
        # Check: status should be draft_ready
        if response['status'] != 'draft_ready':
            result['passed'] = False
            result['reason'] = f"Expected draft_ready, got {response['status']}"
            return result

        # Check: expected keywords present
        answer = response.get('answer_text', '').lower()
        missing_keywords = []
        for kw in test.get('expected_keywords', []):
            if kw.lower() not in answer:
                missing_keywords.append(kw)

        if missing_keywords:
            result['passed'] = False
            result['reason'] = f"Missing expected keywords: {missing_keywords}"
            return result

        # Check: expected citation referenced
        expected_cit = test.get('expected_citation', '')
        if expected_cit:
            citations_text = ' '.join(
                c.get('section_reference', '') for c in response.get('citations', [])
            )
            # Flexible match — check if key parts of the citation appear
            cit_parts = expected_cit.replace('/', ' ').replace('Article', '').replace('Section', '').strip().split()
            answer_and_citations = answer + ' ' + citations_text.lower()
            found_citation = any(part.lower() in answer_and_citations for part in cit_parts if len(part) > 1)

            if not found_citation:
                result['passed'] = False
                result['reason'] = f"Expected citation {expected_cit} not found"
                return result

        result['passed'] = True
        result['detail'] = f"cited correctly, {elapsed:.1f}s"

    elif cat in ('unanswerable', 'cross_community'):
        # Check: status should be needs_human
        if response['status'] != 'needs_human':
            # Check if the response at least says it's not in the docs
            answer = response.get('answer_text', '').lower()
            not_found_phrases = ['not addressed', 'not found', 'not in the documents', 'not covered',
                                 'does not address', 'don\'t have information', 'forwarding',
                                 'not mentioned', 'no information']
            if any(phrase in answer for phrase in not_found_phrases):
                result['passed'] = True
                result['detail'] = f"correct content but status was {response['status']}"
            else:
                result['passed'] = False
                result['reason'] = f"HALLUCINATED: got {response['status']} instead of needs_human"
            return result

        result['passed'] = True
        result['detail'] = f"correctly escalated, {elapsed:.1f}s"

    return result


def _run_unknown_sender_test(test: dict, verbose: bool) -> dict:
    """Test that unknown senders are flagged."""
    # For unknown sender, we simulate the inbound email pipeline
    from .pipeline import process_inbound_email

    try:
        result = process_inbound_email({
            'from': test['tenant_email'],
            'to': 'replivo@agentmail.to',
            'subject': 'Question',
            'body': test['question'],
        })

        if result.get('status') == 'needs_human':
            return {'passed': True, 'detail': 'correctly flagged as unknown sender', 'response': result}
        else:
            return {'passed': False, 'reason': f"Expected needs_human, got {result.get('status')}", 'response': result}
    except Exception as e:
        return {'passed': False, 'reason': f'Exception: {e}'}
