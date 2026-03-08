"""
Simulated in-memory HR database with pre-seeded sample data.
Provides helper functions for CRUD operations across HR entities.
"""

from __future__ import annotations

import threading
from copy import deepcopy
from typing import Optional

from .models import (
    CandidateProfile,
    HRMetrics,
    InterviewSlot,
    LeaveRecord,
    OnboardingTask,
    VerificationReport,
)

_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Sample Resumes (5 domains)
# ---------------------------------------------------------------------------

SAMPLE_RESUMES: list[dict] = [
    {
        "name": "Alice Chen",
        "email": "alice.chen@email.com",
        "education": ["M.S. Computer Science, Stanford University"],
        "skills": ["Python", "Machine Learning", "AWS", "Docker", "REST APIs", "SQL"],
        "previous_roles": ["Senior Software Engineer at Google (3 yrs)", "ML Engineer at Startup (2 yrs)"],
        "years_of_experience": 5,
        "links": ["https://github.com/alicechen", "https://linkedin.com/in/alicechen"],
        "resume_text": "Alice Chen — Software Engineer with 5 years of experience in ML and cloud systems. Built scalable ML pipelines at Google. M.S. CS Stanford."
    },
    {
        "name": "Brian Torres",
        "email": "brian.torres@email.com",
        "education": ["MBA Finance, Wharton School"],
        "skills": ["Financial Modeling", "Risk Analysis", "Bloomberg Terminal", "Python", "Excel VBA"],
        "previous_roles": ["Investment Analyst at JP Morgan (4 yrs)", "Associate at Goldman Sachs (2 yrs)"],
        "years_of_experience": 6,
        "links": ["https://linkedin.com/in/briantorres"],
        "resume_text": "Brian Torres — Finance professional with 6 years in investment banking. Expert in risk analysis and financial modeling. MBA Wharton."
    },
    {
        "name": "Dr. Clara Williams",
        "email": "clara.williams@email.com",
        "education": ["M.D., Johns Hopkins University", "Residency in Internal Medicine"],
        "skills": ["Patient Care", "Clinical Research", "EMR Systems", "Telemedicine", "Medical Documentation"],
        "previous_roles": ["Attending Physician at Mayo Clinic (5 yrs)", "Resident at Johns Hopkins (3 yrs)"],
        "years_of_experience": 8,
        "links": ["https://linkedin.com/in/drclara"],
        "resume_text": "Dr. Clara Williams — Internal Medicine physician with 8 years of clinical experience. Specializes in telemedicine and clinical research. M.D. Johns Hopkins."
    },
    {
        "name": "Derek Patel",
        "email": "derek.patel@email.com",
        "education": ["B.A. Marketing, NYU"],
        "skills": ["SEO", "Google Analytics", "Campaign Strategy", "Content Marketing", "Social Media Ads", "Adobe Creative Suite"],
        "previous_roles": ["Marketing Manager at HubSpot (3 yrs)", "Digital Marketer at Agency (2 yrs)"],
        "years_of_experience": 5,
        "links": ["https://linkedin.com/in/derekpatel", "https://derekpatel.com/portfolio"],
        "resume_text": "Derek Patel — Marketing professional with 5 years specializing in SEO and digital campaigns. Grew organic traffic 240% at HubSpot. B.A. Marketing NYU."
    },
    {
        "name": "Elena Kowalski",
        "email": "elena.kowalski@email.com",
        "education": ["B.S. Industrial Engineering, Purdue University"],
        "skills": ["Lean Manufacturing", "Six Sigma", "AutoCAD", "Supply Chain Management", "Quality Control", "ERP Systems"],
        "previous_roles": ["Production Manager at Toyota (4 yrs)", "Quality Engineer at Boeing (3 yrs)"],
        "years_of_experience": 7,
        "links": ["https://linkedin.com/in/elenakowalski"],
        "resume_text": "Elena Kowalski — Industrial Engineer with 7 years in manufacturing. Six Sigma Black Belt. Led production optimization at Toyota. B.S. IE Purdue."
    },
]

# ---------------------------------------------------------------------------
# Employee Leave Records
# ---------------------------------------------------------------------------

LEAVE_RECORDS: dict[str, LeaveRecord] = {
    "alice chen": LeaveRecord(employee_name="Alice Chen", total_days=24, used_days=5),
    "brian torres": LeaveRecord(employee_name="Brian Torres", total_days=24, used_days=10),
    "clara williams": LeaveRecord(employee_name="Dr. Clara Williams", total_days=24, used_days=2),
    "derek patel": LeaveRecord(employee_name="Derek Patel", total_days=24, used_days=15),
    "elena kowalski": LeaveRecord(employee_name="Elena Kowalski", total_days=24, used_days=8),
}

# ---------------------------------------------------------------------------
# Onboarding Templates
# ---------------------------------------------------------------------------

ONBOARDING_TEMPLATE: list[str] = [
    "Identity Verification",
    "Payroll & Tax Setup",
    "System Access Provisioning",
    "Company Policy Acknowledgement",
    "Team Introduction & Buddy Assignment",
    "IT Equipment Issuance",
    "Benefits Enrollment",
]

# ---------------------------------------------------------------------------
# Runtime State
# ---------------------------------------------------------------------------

_candidates: list[CandidateProfile] = []
_interviews: list[InterviewSlot] = []
_onboarding: dict[str, list[OnboardingTask]] = {}
_verification_reports: dict[str, VerificationReport] = {}
_metrics = HRMetrics()
_uploaded_pdfs: dict[str, dict] = {}  # candidate_name -> {text, links}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_sample_resumes() -> list[dict]:
    return deepcopy(SAMPLE_RESUMES)


def store_candidate(profile: CandidateProfile) -> None:
    with _lock:
        _candidates.append(profile)


def get_candidates() -> list[CandidateProfile]:
    with _lock:
        return deepcopy(_candidates)


def store_uploaded_pdf(candidate_name: str, text: str, links: list[str]) -> None:
    with _lock:
        _uploaded_pdfs[candidate_name.lower()] = {"text": text, "links": links}


def get_uploaded_pdf(candidate_name: str) -> Optional[dict]:
    with _lock:
        return _uploaded_pdfs.get(candidate_name.lower())


def get_all_uploaded_pdfs() -> dict[str, dict]:
    with _lock:
        return deepcopy(_uploaded_pdfs)


# -- Leave ---------------------------------------------------------------

def get_leave_record(employee_name: str) -> Optional[LeaveRecord]:
    with _lock:
        return deepcopy(LEAVE_RECORDS.get(employee_name.lower()))


def update_leave(employee_name: str, days: int) -> str:
    with _lock:
        key = employee_name.lower()
        record = LEAVE_RECORDS.get(key)
        if not record:
            return f"No leave record found for '{employee_name}'."
        if days > record.balance:
            return f"Insufficient leave balance. {record.employee_name} has {record.balance} days remaining."
        record.used_days += days
        return f"Leave approved for {record.employee_name}. {days} day(s) deducted. Remaining balance: {record.balance} days."


# -- Interviews ----------------------------------------------------------

def store_interview(slot: InterviewSlot) -> None:
    with _lock:
        _interviews.append(slot)


def get_interviews() -> list[InterviewSlot]:
    with _lock:
        return deepcopy(_interviews)


# -- Onboarding ---------------------------------------------------------

def get_onboarding_tasks(employee_name: str) -> list[OnboardingTask]:
    with _lock:
        key = employee_name.lower()
        if key not in _onboarding:
            _onboarding[key] = [
                OnboardingTask(employee_name=employee_name, task_name=t)
                for t in ONBOARDING_TEMPLATE
            ]
        return deepcopy(_onboarding[key])


def update_onboarding_task(employee_name: str, task_name: str) -> str:
    with _lock:
        key = employee_name.lower()
        if key not in _onboarding:
            _onboarding[key] = [
                OnboardingTask(employee_name=employee_name, task_name=t)
                for t in ONBOARDING_TEMPLATE
            ]
        for task in _onboarding[key]:
            if task.task_name.lower() == task_name.lower():
                task.completed = True
                return f"Onboarding task '{task_name}' marked complete for {employee_name}."
        return f"Task '{task_name}' not found in onboarding checklist for {employee_name}."


# -- Verification --------------------------------------------------------

def store_verification_report(report: VerificationReport) -> None:
    with _lock:
        _verification_reports[report.candidate_name.lower()] = report


def get_verification_report(candidate_name: str) -> Optional[VerificationReport]:
    with _lock:
        return deepcopy(_verification_reports.get(candidate_name.lower()))


# -- Metrics -------------------------------------------------------------

def get_metrics() -> HRMetrics:
    with _lock:
        return deepcopy(_metrics)


def increment_metric(field: str, count: int = 1) -> None:
    with _lock:
        current = getattr(_metrics, field, None)
        if current is not None:
            setattr(_metrics, field, current + count)
