"""
Test fixtures for Replivo AI response engine.

Three sample communities under one org ("Jason's Property Management"),
each with their own CC&R document. Tests verify:
1. Answerable questions get correct, cited responses
2. Unanswerable questions are flagged — NO hallucination
3. Cross-community isolation (tenant A doesn't get community B's docs)
"""

# ---------------------------------------------------------------------------
# Organization & Communities
# ---------------------------------------------------------------------------

TEST_ORG = {
    "name": "Jason's Property Management",
    "slug": "jasons-pm",
}

TEST_COMMUNITIES = [
    {
        "name": "Mission Street Condos",
        "slug": "mission-street",
        "document": "samples/mission-street-ccr.pdf",
        "description": "24-unit mixed-use condo in San Francisco (1587 15th St / 1905-1911 Mission St)",
    },
    {
        "name": "Timber Ridge HOA",
        "slug": "timber-ridge",
        "document": "samples/timber-ridge-ccr.pdf",
        "description": "Rural subdivision in Archuleta County, Colorado (Pagosa Springs area)",
    },
    {
        "name": "Gleneagle Estates",
        "slug": "gleneagle",
        "document": "samples/gleneagle-ccr.pdf",
        "description": "Residential community in El Paso County, Colorado (Colorado Springs area)",
    },
]

# ---------------------------------------------------------------------------
# Test tenants
# ---------------------------------------------------------------------------

TEST_TENANTS = [
    # Mission Street
    {"email": "alice@example.com", "name": "Alice Chen", "unit": "Unit 31", "community": "mission-street"},
    {"email": "bob@example.com", "name": "Bob Martinez", "unit": "Unit 46", "community": "mission-street"},
    # Timber Ridge
    {"email": "carol@example.com", "name": "Carol Davis", "unit": "Lot 12", "community": "timber-ridge"},
    {"email": "dan@example.com", "name": "Dan Wilson", "unit": "Lot 7", "community": "timber-ridge"},
    # Gleneagle
    {"email": "eve@example.com", "name": "Eve Johnson", "unit": "14 Eagle Dr", "community": "gleneagle"},
    # Unknown sender (not in any community)
    {"email": "stranger@example.com", "name": "Unknown Person", "unit": None, "community": None},
]


# ---------------------------------------------------------------------------
# Test questions
#
# Each test case has:
#   - community: which community's docs to search
#   - tenant_email: who is asking
#   - question: the email body
#   - answerable: True if the answer IS in the docs, False if NOT
#   - expected_keywords: phrases that MUST appear in a correct answer (for answerable)
#   - expected_citation: article/section that should be cited (for answerable)
#   - trap_description: what the AI might hallucinate if not grounded (for unanswerable)
# ---------------------------------------------------------------------------

ANSWERABLE_QUESTIONS = [
    # ===== MISSION STREET CONDOS =====
    {
        "community": "mission-street",
        "tenant_email": "alice@example.com",
        "question": "Can I have a dog in my unit?",
        "answerable": True,
        "expected_keywords": ["two", "dogs or cats", "total of two"],
        "expected_citation": "Section 7.6",
        "notes": "Max 2 dogs or cats total per unit. Certain breeds banned (Pit Bull, Rottweiler, etc).",
    },
    {
        "community": "mission-street",
        "tenant_email": "alice@example.com",
        "question": "What breeds of dogs are not allowed?",
        "answerable": True,
        "expected_keywords": ["Pit Bull", "Rottweiler", "Doberman", "Mastiff", "Presa Canaria"],
        "expected_citation": "Section 7.6",
        "notes": "Prohibited: Pit Bull, Presa Canaria, Rottweiler, Doberman Pinscher, Mastiff, and any other fighting breed.",
    },
    {
        "community": "mission-street",
        "tenant_email": "alice@example.com",
        "question": "Can I rent out my condo on Airbnb for a weekend?",
        "answerable": True,
        "expected_keywords": ["30 days", "less than 30 days", "not", "transient"],
        "expected_citation": "Section 7.8",
        "notes": "No rental for less than 30 days or for transient/hotel purposes.",
    },
    {
        "community": "mission-street",
        "tenant_email": "bob@example.com",
        "question": "Do I need approval to renovate my kitchen?",
        "answerable": True,
        "expected_keywords": ["approval", "Board", "improvement"],
        "expected_citation": "Article 6 / Section 6.1",
        "notes": "Prior written Board approval required for any improvements or modifications.",
    },
    {
        "community": "mission-street",
        "tenant_email": "bob@example.com",
        "question": "Can I hang clothes on my balcony to dry?",
        "answerable": True,
        "expected_keywords": ["not permitted", "clothing", "laundry"],
        "expected_citation": "Section 7.9",
        "notes": "Outside laundering or drying of clothes is not permitted.",
    },
    {
        "community": "mission-street",
        "tenant_email": "alice@example.com",
        "question": "What happens if I don't pay my assessment on time?",
        "answerable": True,
        "expected_keywords": ["15 days", "10 percent", "late charge", "12 percent", "interest"],
        "expected_citation": "Section 4.9",
        "notes": "Delinquent after 15 days; 10% late charge or $10 min; 12% annual interest after 30 days.",
    },
    {
        "community": "mission-street",
        "tenant_email": "alice@example.com",
        "question": "Can I use a charcoal grill on my balcony?",
        "answerable": True,
        "expected_keywords": ["charcoal", "not", "barbecue"],
        "expected_citation": "Section 7.13",
        "notes": "Charcoal barbecues may not be used on decks or balconies.",
    },
    {
        "community": "mission-street",
        "tenant_email": "alice@example.com",
        "question": "What color can my window coverings be?",
        "answerable": True,
        "expected_keywords": ["neutral", "color"],
        "expected_citation": "Section 7.12",
        "notes": "Window coverings visible from street or Common Area must be neutral color.",
    },
    {
        "community": "mission-street",
        "tenant_email": "bob@example.com",
        "question": "Can I put a For Sale sign in my window?",
        "answerable": True,
        "expected_keywords": ["five square feet", "For Sale"],
        "expected_citation": "Section 7.5",
        "notes": "For Sale or For Rent signs allowed, max 5 sq ft.",
    },
    {
        "community": "mission-street",
        "tenant_email": "alice@example.com",
        "question": "Can I install a satellite dish?",
        "answerable": True,
        "expected_keywords": ["one meter", "approval", "Board"],
        "expected_citation": "Section 6.4 / Section 7.10",
        "notes": "Dishes ≤1m subject to Civil Code 1376; larger dishes need Board approval.",
    },
    {
        "community": "mission-street",
        "tenant_email": "bob@example.com",
        "question": "Do I need carpet in my unit? What are the flooring requirements?",
        "answerable": True,
        "expected_keywords": ["80 percent", "carpet", "noise", "pad"],
        "expected_citation": "Section 7.14",
        "notes": "80% of hallway/room floor (except kitchen/bath) must have carpet and pad for sound.",
    },

    # ===== TIMBER RIDGE HOA =====
    {
        "community": "timber-ridge",
        "tenant_email": "carol@example.com",
        "question": "Can I paint my house bright blue?",
        "answerable": True,
        "expected_keywords": ["natural", "earth tones", "IRC", "approval"],
        "expected_citation": "Article VIII.I",
        "notes": "Colors must be natural/earth tones. IRC approval required for all exterior colors.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "carol@example.com",
        "question": "How many dogs can I have?",
        "answerable": True,
        "expected_keywords": ["three", "3", "dogs"],
        "expected_citation": "Article X.H",
        "notes": "Max 3 dogs and/or 3 cats per household.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "dan@example.com",
        "question": "Can I do short term rentals like Airbnb?",
        "answerable": True,
        "expected_keywords": ["less than 30 days", "not allowed", "prohibited", "short-term"],
        "expected_citation": "Article VII.E",
        "notes": "Short-term rentals under 30 days are prohibited.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "carol@example.com",
        "question": "How tall can my fence be?",
        "answerable": True,
        "expected_keywords": ["42 inches", "IRC", "boundary"],
        "expected_citation": "Article VIII.L",
        "notes": "Boundary/perimeter fences max 42 inches. Non-boundary at IRC discretion.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "dan@example.com",
        "question": "Can I cut down a large tree on my lot?",
        "answerable": True,
        "expected_keywords": ["5 inches", "diameter", "IRC", "written permission"],
        "expected_citation": "Article VIII.O",
        "notes": "Trees >5 inch diameter (at 4.5ft) need written IRC permission to remove.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "carol@example.com",
        "question": "What is the minimum house size I can build?",
        "answerable": True,
        "expected_keywords": ["2,300", "2,800", "square feet"],
        "expected_citation": "Article VIII.D",
        "notes": "2,300 sq ft with attached garage, 2,800 sq ft with detached garage.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "dan@example.com",
        "question": "Can I keep chickens on my lot?",
        "answerable": True,
        "expected_keywords": ["no", "barnyard animals", "chickens", "not"],
        "expected_citation": "Article X.E",
        "notes": "No chickens, pigs, goats, rabbits. Exception only for 4-H projects with IRC variance.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "carol@example.com",
        "question": "Can I use barbed wire for fencing?",
        "answerable": True,
        "expected_keywords": ["no", "barbed wire", "not allowed"],
        "expected_citation": "Article VIII.L",
        "notes": "No chain link or barbed wire. Exception: chain link dog runs.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "dan@example.com",
        "question": "How long can I park my RV outside the garage?",
        "answerable": True,
        "expected_keywords": ["45 days", "annually"],
        "expected_citation": "Article VIII.H",
        "notes": "Owner RVs max 45 days/year outside. 7 days for maintenance. Guest RVs 30 days.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "carol@example.com",
        "question": "What is the maximum building height?",
        "answerable": True,
        "expected_keywords": ["35 feet"],
        "expected_citation": "Article VIII.E",
        "notes": "35 feet, measured per Uniform Building Code.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "dan@example.com",
        "question": "Can I run a business from my home?",
        "answerable": True,
        "expected_keywords": ["500 square feet", "home business"],
        "expected_citation": "Article VII.E",
        "notes": "Home business allowed with conditions: ≤500 sq ft, no odors/noise, no extra traffic, no employees other than residents, no signs.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "carol@example.com",
        "question": "Is alcohol allowed at the clubhouse?",
        "answerable": True,
        "expected_keywords": ["alcohol-free", "Common Properties", "Special Event Permit"],
        "expected_citation": "Article XI.A.3 / XI.A.9",
        "notes": "Common Properties are alcohol-free unless IRC grants a Special Event Permit.",
    },

    # ===== GLENEAGLE =====
    {
        "community": "gleneagle",
        "tenant_email": "eve@example.com",
        "question": "How many pets can I have?",
        "answerable": True,
        "expected_keywords": ["2", "two", "dogs or cats"],
        "expected_citation": "Section 137.b",
        "notes": "Max 2 domesticated dogs or cats.",
    },
    {
        "community": "gleneagle",
        "tenant_email": "eve@example.com",
        "question": "Can I park my boat in my driveway?",
        "answerable": True,
        "expected_keywords": ["enclosed garage", "screened", "not", "boat"],
        "expected_citation": "Section 137.c",
        "notes": "No boats/trailers/campers except in completely enclosed garage or fully screened.",
    },
    {
        "community": "gleneagle",
        "tenant_email": "eve@example.com",
        "question": "Do I need to keep my garage door closed?",
        "answerable": True,
        "expected_keywords": ["closed", "garage door", "remote control", "electronic"],
        "expected_citation": "Section 128",
        "notes": "Garage doors must be kept closed except when entering/exiting. All must have electronic remote.",
    },
    {
        "community": "gleneagle",
        "tenant_email": "eve@example.com",
        "question": "What is the minimum house size for a single-story home with a basement?",
        "answerable": True,
        "expected_keywords": ["1,500", "square feet"],
        "expected_citation": "Section 117",
        "notes": "Ranch/single story with basement: 1,500 sq ft.",
    },
]


UNANSWERABLE_QUESTIONS = [
    # ===== MISSION STREET — NOT IN DOC =====
    {
        "community": "mission-street",
        "tenant_email": "alice@example.com",
        "question": "What are the pool hours?",
        "answerable": False,
        "trap_description": "AI might invent pool hours. There is no pool mentioned in the Mission Street CC&Rs.",
    },
    {
        "community": "mission-street",
        "tenant_email": "alice@example.com",
        "question": "How much are the monthly HOA dues?",
        "answerable": False,
        "trap_description": "AI might guess a dollar amount. The CC&Rs describe the assessment structure but never specify a dollar amount for dues.",
    },
    {
        "community": "mission-street",
        "tenant_email": "bob@example.com",
        "question": "What are the quiet hours in the building?",
        "answerable": False,
        "trap_description": "AI might invent hours like 10pm-8am. The CC&Rs mention nuisance (7.4) but define NO specific quiet hours.",
    },
    {
        "community": "mission-street",
        "tenant_email": "alice@example.com",
        "question": "Can I install solar panels on the roof?",
        "answerable": False,
        "trap_description": "AI might guess based on general knowledge. Solar panels are not addressed in the Mission Street CC&Rs.",
    },
    {
        "community": "mission-street",
        "tenant_email": "bob@example.com",
        "question": "Is there a gym in the building?",
        "answerable": False,
        "trap_description": "AI might invent amenities. No gym or fitness center is mentioned in the CC&Rs.",
    },
    {
        "community": "mission-street",
        "tenant_email": "alice@example.com",
        "question": "Can I have a holiday party in the common area?",
        "answerable": False,
        "trap_description": "AI might make up event policies. The CC&Rs don't address common area event reservations or parties.",
    },
    {
        "community": "mission-street",
        "tenant_email": "alice@example.com",
        "question": "What's the move-in/move-out procedure?",
        "answerable": False,
        "trap_description": "AI might invent elevator reservation or moving hours. Not addressed in the CC&Rs.",
    },

    # ===== TIMBER RIDGE — NOT IN DOC =====
    {
        "community": "timber-ridge",
        "tenant_email": "carol@example.com",
        "question": "What is the speed limit on the roads in the subdivision?",
        "answerable": False,
        "trap_description": "AI might guess 25 mph or similar. No speed limits are defined in the CC&Rs.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "dan@example.com",
        "question": "Can I put up Christmas lights on my house?",
        "answerable": False,
        "trap_description": "AI might invent holiday decoration rules. Not addressed in the CC&Rs.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "carol@example.com",
        "question": "Can I install a basketball hoop in my driveway?",
        "answerable": False,
        "trap_description": "AI might guess based on general HOA knowledge. Basketball hoops/play structures not addressed.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "carol@example.com",
        "question": "Do I need to shovel snow from my sidewalk?",
        "answerable": False,
        "trap_description": "AI might invent snow removal rules. Snow removal is not addressed in the CC&Rs.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "dan@example.com",
        "question": "Can I put a political sign in my yard during election season?",
        "answerable": False,
        "trap_description": "AI might invent political sign rules. The CC&Rs only address For Sale signs, residential ID signs, and contractor signs. Political signs are not mentioned.",
    },
    {
        "community": "timber-ridge",
        "tenant_email": "carol@example.com",
        "question": "Can I install a security camera that points at the street?",
        "answerable": False,
        "trap_description": "AI might guess about security camera/surveillance rules. Not addressed.",
    },

    # ===== GLENEAGLE — NOT IN DOC =====
    {
        "community": "gleneagle",
        "tenant_email": "eve@example.com",
        "question": "What color can I paint my front door?",
        "answerable": False,
        "trap_description": "AI might invent approved colors. The Gleneagle CC&Rs discuss architectural style but do not specify paint colors for doors.",
    },
    {
        "community": "gleneagle",
        "tenant_email": "eve@example.com",
        "question": "How much are the annual dues?",
        "answerable": False,
        "trap_description": "AI might guess a dollar amount. No specific dues amounts in the CC&Rs.",
    },
]


CROSS_COMMUNITY_QUESTIONS = [
    # A Timber Ridge tenant asking something only in Mission Street docs
    {
        "community": "timber-ridge",
        "tenant_email": "carol@example.com",
        "question": "What are the parking stacker rules?",
        "answerable": False,
        "trap_description": "Parking stackers are a Mission Street feature (Section 7.3/4.7D). Timber Ridge has no parking stackers. AI must NOT reference Mission Street docs.",
    },
    # A Mission Street tenant asking something only in Timber Ridge docs
    {
        "community": "mission-street",
        "tenant_email": "alice@example.com",
        "question": "Can I keep horses on my property?",
        "answerable": False,
        "trap_description": "Horses are addressed in Timber Ridge (Article X.D). Mission Street is a condo — no horse rules. AI must NOT reference Timber Ridge docs.",
    },
    # A Gleneagle tenant asking something specific to Timber Ridge
    {
        "community": "gleneagle",
        "tenant_email": "eve@example.com",
        "question": "What is the defensible fire zone requirement around my house?",
        "answerable": False,
        "trap_description": "Defensible fire zone (30ft/60ft) is in Timber Ridge (Article VIII.K). Not in Gleneagle CC&Rs. AI must NOT reference Timber Ridge docs.",
    },
]


UNKNOWN_SENDER_QUESTIONS = [
    {
        "community": None,
        "tenant_email": "stranger@example.com",
        "question": "Can I paint my house?",
        "answerable": False,
        "trap_description": "Sender not recognized as a tenant in any community. System should flag as unknown sender and NOT attempt to answer.",
        "expected_status": "needs_human",
    },
]


# ---------------------------------------------------------------------------
# All questions combined for test runner
# ---------------------------------------------------------------------------

ALL_TEST_CASES = (
    [dict(category="answerable", **q) for q in ANSWERABLE_QUESTIONS]
    + [dict(category="unanswerable", **q) for q in UNANSWERABLE_QUESTIONS]
    + [dict(category="cross_community", **q) for q in CROSS_COMMUNITY_QUESTIONS]
    + [dict(category="unknown_sender", **q) for q in UNKNOWN_SENDER_QUESTIONS]
)
