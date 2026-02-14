"""Replivo CLI — development, testing, and admin commands."""
import sys
import os
import argparse

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))


def get_app():
    from backend.app import create_app
    return create_app()


def cmd_seed(args):
    """Seed database with test org, communities, tenants."""
    app = get_app()
    with app.app_context():
        from backend.app.extensions import db
        from backend.app.models import Organization, User, Community, Tenant

        # Check if already seeded
        existing = Organization.query.filter_by(slug='jasons-pm').first()
        if existing:
            print("Database already seeded. Use --force to re-seed.")
            if not args.force:
                return
            # Drop and re-create
            print("Force re-seeding...")
            db.drop_all()
            db.create_all()

        from tests.test_fixtures import TEST_ORG, TEST_COMMUNITIES, TEST_TENANTS

        # Create org
        org = Organization(name=TEST_ORG['name'], slug=TEST_ORG['slug'])
        db.session.add(org)
        db.session.flush()

        # Create admin user
        admin = User(
            organization_id=org.id,
            email='admin@replivo.com',
            username='admin',
            role='owner',
        )
        admin.set_password('admin')
        db.session.add(admin)

        # Create communities
        community_map = {}
        for c in TEST_COMMUNITIES:
            community = Community(
                organization_id=org.id,
                name=c['name'],
                slug=c['slug'],
                description=c.get('description', ''),
                inbox_email='replivo@agentmail.to',
                settings={'auto_reply_enabled': True},
            )
            db.session.add(community)
            db.session.flush()
            community_map[c['slug']] = community
            print(f"  Created community: {c['name']}")

        # Create tenants
        for t in TEST_TENANTS:
            if t['community'] is None:
                continue  # Skip unknown sender
            community = community_map.get(t['community'])
            if not community:
                continue
            tenant = Tenant(
                community_id=community.id,
                name=t['name'],
                email=t['email'],
                unit=t['unit'],
            )
            db.session.add(tenant)
            print(f"  Created tenant: {t['name']} ({t['email']}) in {t['community']}")

        db.session.commit()
        print(f"\nSeeded: 1 org, 1 admin (admin/admin), {len(community_map)} communities, {len([t for t in TEST_TENANTS if t['community']])} tenants")

        if args.with_documents:
            print("\nIngesting sample documents...")
            from backend.app.services.document_service import ingest_document
            for c in TEST_COMMUNITIES:
                doc_path = os.path.join(PROJECT_ROOT, c['document'])
                if os.path.exists(doc_path):
                    community = community_map[c['slug']]
                    print(f"  Ingesting {c['document']} for {c['name']}...")
                    ingest_document(community.id, doc_path)
                    print(f"    Done.")
                else:
                    print(f"  WARNING: {doc_path} not found, skipping")


def cmd_communities(args):
    """List all communities."""
    app = get_app()
    with app.app_context():
        from backend.app.models import Community
        communities = Community.query.all()
        if not communities:
            print("No communities found. Run `cli seed` first.")
            return
        print(f"\n{'Name':<30} {'Slug':<20} {'Tenants':<10} {'Documents':<10}")
        print("-" * 75)
        for c in communities:
            print(f"{c.name:<30} {c.slug:<20} {c.tenants.count():<10} {c.documents.count():<10}")
        print()


def cmd_documents(args):
    """List documents for a community."""
    app = get_app()
    with app.app_context():
        from backend.app.models import Community
        community = Community.query.filter_by(slug=args.community).first()
        if not community:
            print(f"Community '{args.community}' not found.")
            return
        docs = community.documents.all()
        if not docs:
            print(f"No documents for {community.name}.")
            return
        print(f"\nDocuments for {community.name}:")
        for d in docs:
            print(f"  {d.filename} — {d.total_chunks} chunks, {d.total_tokens} tokens, status: {d.status}")
        print()


def cmd_ingest(args):
    """Ingest a document into a community."""
    app = get_app()
    with app.app_context():
        from backend.app.models import Community
        from backend.app.services.document_service import ingest_document

        community = Community.query.filter_by(slug=args.community).first()
        if not community:
            print(f"Community '{args.community}' not found.")
            return

        filepath = os.path.abspath(args.file)
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return

        print(f"Ingesting {filepath} into {community.name}...")
        doc = ingest_document(community.id, filepath)
        print(f"Done: {doc.total_chunks} chunks, {doc.total_tokens} tokens")


def cmd_ask(args):
    """Ask a question against a community's documents."""
    app = get_app()
    with app.app_context():
        from backend.app.models import Community
        from backend.app.services.pipeline import process_question

        community = Community.query.filter_by(slug=args.community).first()
        if not community:
            print(f"Community '{args.community}' not found.")
            return

        tenant_email = args.email or 'cli@replivo.com'
        print(f"\nAsking: {args.question}")
        print(f"Community: {community.name}")
        print(f"Tenant: {tenant_email}")
        print("-" * 60)

        result = process_question(community.id, args.question, tenant_email)

        if args.raw:
            import json
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"\nStatus: {result['status']}")
            if result.get('escalation_reason'):
                print(f"Escalation: {result['escalation_reason']}")
            print(f"\nResponse:\n{result['answer_text']}")
            if result.get('citations'):
                print(f"\nCitations:")
                for c in result['citations']:
                    print(f"  - {c.get('section_reference', 'N/A')}: {c.get('claim_text', '')[:80]}")
        print()


def cmd_test(args):
    """Run grounding test suite."""
    app = get_app()
    with app.app_context():
        from backend.app.services.test_runner import run_tests
        run_tests(
            category=args.category,
            community=args.community,
            verbose=args.verbose,
        )


def cmd_simulate_email(args):
    """Simulate an inbound email through the full pipeline."""
    app = get_app()
    with app.app_context():
        from backend.app.services.pipeline import process_inbound_email
        result = process_inbound_email({
            'from': args.sender,
            'to': args.to,
            'subject': args.subject,
            'body': args.body,
        })
        print(f"Processed. Conversation status: {result.get('status', 'unknown')}")


def cmd_conversations(args):
    """List recent conversations."""
    app = get_app()
    with app.app_context():
        from backend.app.models import Conversation
        convos = Conversation.query.order_by(Conversation.updated_at.desc()).limit(20).all()
        if not convos:
            print("No conversations found.")
            return
        print(f"\n{'ID':<38} {'Status':<15} {'From':<25} {'Subject':<30}")
        print("-" * 110)
        for c in convos:
            print(f"{c.id:<38} {c.status:<15} {c.sender_email:<25} {c.subject[:30]:<30}")
        print()


def main():
    parser = argparse.ArgumentParser(prog='cli', description='Replivo CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # seed
    sp = subparsers.add_parser('seed', help='Seed database')
    sp.add_argument('--with-documents', action='store_true', help='Also ingest sample CC&R PDFs')
    sp.add_argument('--force', action='store_true', help='Force re-seed (drops all data)')

    # communities
    subparsers.add_parser('communities', help='List communities')

    # documents
    sp = subparsers.add_parser('documents', help='List documents for a community')
    sp.add_argument('community', help='Community slug')

    # ingest
    sp = subparsers.add_parser('ingest', help='Ingest a document')
    sp.add_argument('community', help='Community slug')
    sp.add_argument('file', help='Path to PDF or text file')

    # ask
    sp = subparsers.add_parser('ask', help='Ask a question')
    sp.add_argument('community', help='Community slug')
    sp.add_argument('question', help='The question to ask')
    sp.add_argument('--email', help='Simulate as this tenant email')
    sp.add_argument('--raw', action='store_true', help='Show raw LLM output')

    # test
    sp = subparsers.add_parser('test', help='Run grounding test suite')
    sp.add_argument('--category', choices=['answerable', 'unanswerable', 'cross_community', 'unknown_sender'])
    sp.add_argument('--community', help='Filter by community slug')
    sp.add_argument('--verbose', action='store_true', help='Show full responses')

    # simulate-email
    sp = subparsers.add_parser('simulate-email', help='Simulate inbound email')
    sp.add_argument('--from', dest='sender', required=True)
    sp.add_argument('--to', default='replivo@agentmail.to')
    sp.add_argument('--subject', default='Question')
    sp.add_argument('--body', required=True)

    # conversations
    subparsers.add_parser('conversations', help='List conversations')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    commands = {
        'seed': cmd_seed,
        'communities': cmd_communities,
        'documents': cmd_documents,
        'ingest': cmd_ingest,
        'ask': cmd_ask,
        'test': cmd_test,
        'simulate-email': cmd_simulate_email,
        'conversations': cmd_conversations,
    }
    commands[args.command](args)


if __name__ == '__main__':
    main()
