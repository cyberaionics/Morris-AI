"""
HR Policy Knowledge Base.
Provides keyword-based retrieval over a small corpus of HR policies.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Policy Corpus
# ---------------------------------------------------------------------------

POLICIES: dict[str, str] = {
    "leave policy": (
        "LEAVE POLICY\n\n"
        "All full-time employees are entitled to 24 paid leave days per calendar year.\n"
        "Leave accrues at 2 days per month. Unused leave can be carried forward up to a maximum of 10 days.\n"
        "Leave requests must be submitted at least 3 business days in advance for planned leave.\n"
        "Emergency leave may be granted at the manager's discretion.\n"
        "Half-day leave is available. Leave without pay (LWP) requires HR Director approval."
    ),
    "maternity policy": (
        "MATERNITY & PATERNITY LEAVE POLICY\n\n"
        "Maternity leave: 26 weeks of paid leave for birth mothers.\n"
        "Paternity leave: 4 weeks of paid leave for fathers/partners.\n"
        "Adoptive parents receive 12 weeks of paid leave.\n"
        "Leave begins from the date of delivery or placement.\n"
        "Employees must notify HR at least 8 weeks before the expected date.\n"
        "Flexible return-to-work arrangements are available upon request."
    ),
    "reimbursement policy": (
        "REIMBURSEMENT POLICY\n\n"
        "Employees may claim reimbursement for approved business expenses.\n"
        "Submit reimbursement requests within 30 days of the expense.\n"
        "Required documentation: original receipts, purpose of expense, approval from manager.\n"
        "Categories: travel, meals (up to $75/day), office supplies, professional development.\n"
        "Reimbursements are processed within 10 business days.\n"
        "For expenses over $500, pre-approval from the Finance department is required."
    ),
    "remote work policy": (
        "REMOTE WORK POLICY\n\n"
        "Eligible employees may work remotely up to 3 days per week with manager approval.\n"
        "A stable internet connection and a suitable workspace are required.\n"
        "Core collaboration hours: 10:00 AM – 3:00 PM in the employee's local timezone.\n"
        "Fully remote roles may be approved on a case-by-case basis.\n"
        "Equipment: the company provides a laptop and one monitor for remote workers.\n"
        "Employees must comply with data security policies when working remotely."
    ),
    "code of conduct": (
        "CODE OF CONDUCT\n\n"
        "All employees are expected to maintain professionalism, integrity, and respect.\n"
        "Harassment, discrimination, and retaliation are strictly prohibited.\n"
        "Conflicts of interest must be disclosed to HR immediately.\n"
        "Confidential information must be safeguarded per the NDA.\n"
        "Violations may result in disciplinary action up to and including termination.\n"
        "An anonymous ethics hotline is available for reporting concerns."
    ),
    "performance review policy": (
        "PERFORMANCE REVIEW POLICY\n\n"
        "Performance reviews are conducted semi-annually in June and December.\n"
        "The process includes self-assessment, peer feedback, and manager evaluation.\n"
        "Ratings: Exceeds Expectations, Meets Expectations, Needs Improvement.\n"
        "A Performance Improvement Plan (PIP) may be initiated for underperforming employees.\n"
        "Reviews are linked to compensation adjustments and promotion eligibility.\n"
        "Employees may request a skip-level review with HR if they disagree with their rating."
    ),
    "benefits policy": (
        "BENEFITS POLICY\n\n"
        "Full-time employees are eligible for: health insurance (medical, dental, vision),\n"
        "401(k) retirement plan with 4% company match, life insurance, disability coverage.\n"
        "Benefits enrollment occurs within 30 days of hire and during annual open enrollment.\n"
        "Dependents may be added during qualifying life events.\n"
        "Wellness stipend: $500/year for gym memberships, fitness equipment, or wellness apps.\n"
        "Employee Assistance Program (EAP) provides free confidential counseling."
    ),
}

# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def policy_search(query: str) -> str:
    """Search the HR knowledge base for the most relevant policy.

    Uses keyword overlap scoring to find the best match.

    Args:
        query: Natural language question about HR policies.

    Returns:
        The most relevant policy text, or a fallback message.
    """
    query_lower = query.lower()
    query_words = set(query_lower.split())

    best_score = 0
    best_policy = ""

    for key, text in POLICIES.items():
        key_words = set(key.split())
        # Score = number of query words that appear in the policy key or text
        score = len(query_words & key_words)
        # Also check if query words appear in the policy body
        text_lower = text.lower()
        for word in query_words:
            if len(word) > 3 and word in text_lower:
                score += 0.5

        if score > best_score:
            best_score = score
            best_policy = text

    if best_score > 0:
        return best_policy

    # Fallback: return all policy names
    available = ", ".join(POLICIES.keys())
    return (
        f"I couldn't find a specific policy matching your query. "
        f"Available policies: {available}. "
        f"Please refine your question or ask about one of these topics."
    )
