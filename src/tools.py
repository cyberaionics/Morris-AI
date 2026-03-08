"""
LangChain tool registry.
Aggregates all HR tools into a single list for the agent.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from . import database as db
from .email_service import send_email as _send_email
from .job_parser import job_description_parser as _jd_parser
from .knowledge_base import policy_search as _policy_search
from .matcher import candidate_matcher as _matcher
from .resume_parser import resume_parser as _resume_parser
from .scheduler import schedule_interview as _schedule
from .verification_agent import verify_resume_links as _verify_links

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool Definitions
# ---------------------------------------------------------------------------

@tool
def resume_parser(resume_text: str) -> str:
    """Parse resume text and extract structured candidate information including name, email, skills, education, experience, and links."""
    db.increment_metric("resumes_screened")
    return _resume_parser(resume_text)


@tool
def job_description_parser(job_description: str) -> str:
    """Parse a job description and extract structured requirements including required skills, responsibilities, experience level, and domain."""
    return _jd_parser(job_description)


@tool
def candidate_matcher(candidate_profile: str, job_requirements: str) -> str:
    """Evaluate a candidate against job requirements and return a compatibility score (0-100) with detailed reasoning."""
    result = _matcher(candidate_profile, job_requirements)
    try:
        data = json.loads(result)
        if data.get("score", 0) >= 70:
            db.increment_metric("candidates_shortlisted")
    except (json.JSONDecodeError, TypeError):
        pass
    return result


@tool
def schedule_interview(candidate_email: str, interviewer_email: str) -> str:
    """Schedule an interview between a candidate and an interviewer. Returns the confirmed time slot."""
    return _schedule(candidate_email, interviewer_email)


@tool
def send_email(recipient: str, subject: str, body: str) -> str:
    """Send a professional HR email to the specified recipient. Simulates delivery and returns confirmation."""
    return _send_email(recipient, subject, body)


@tool
def update_onboarding(employee_name: str, task_name: str) -> str:
    """Mark an onboarding checklist task as completed for an employee. Tasks include: Identity Verification, Payroll & Tax Setup, System Access Provisioning, Company Policy Acknowledgement, Team Introduction & Buddy Assignment, IT Equipment Issuance, Benefits Enrollment."""
    return db.update_onboarding_task(employee_name, task_name)


@tool
def get_onboarding_status(employee_name: str) -> str:
    """Get the current onboarding checklist status for an employee, showing all tasks and their completion state."""
    tasks = db.get_onboarding_tasks(employee_name)
    if not tasks:
        return f"No onboarding record found for {employee_name}."
    lines = [f"📋 Onboarding Status for {employee_name}:"]
    for t in tasks:
        status = "✅" if t.completed else "⬜"
        lines.append(f"  {status} {t.task_name}")
    completed = sum(1 for t in tasks if t.completed)
    lines.append(f"\nProgress: {completed}/{len(tasks)} tasks completed")
    return "\n".join(lines)


@tool
def leave_manager(employee_name: str, days_requested: int) -> str:
    """Process a leave request for an employee. Checks leave balance, approves or rejects the request, and updates records."""
    record = db.get_leave_record(employee_name)
    if not record:
        return f"No leave record found for '{employee_name}'. Please check the employee name."
    if days_requested <= 0:
        return "Invalid request: days must be greater than 0."
    return db.update_leave(employee_name, days_requested)


@tool
def check_leave_balance(employee_name: str) -> str:
    """Check the remaining leave balance for an employee."""
    record = db.get_leave_record(employee_name)
    if not record:
        return f"No leave record found for '{employee_name}'."
    return (
        f"📅 Leave Balance for {record.employee_name}:\n"
        f"  Total annual days: {record.total_days}\n"
        f"  Used: {record.used_days}\n"
        f"  Remaining: {record.balance} days"
    )


@tool
def policy_search(query: str) -> str:
    """Search the HR knowledge base for policy information. Covers: leave policy, maternity/paternity policy, reimbursement policy, remote work policy, code of conduct, performance review policy, and benefits policy."""
    return _policy_search(query)


@tool
def generate_document(employee_name: str, document_type: str) -> str:
    """Generate an HR document for an employee. Supported types: offer_letter, onboarding_instructions, employment_confirmation, promotion_letter, experience_letter."""
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        prompt = (
            f"Generate a professional HR {document_type.replace('_', ' ')} "
            f"for employee '{employee_name}'. "
            f"Use a formal business tone. Include the current date. "
            f"Use [Company Name] as a placeholder for the company name."
        )
        response = llm.invoke([{"role": "user", "content": prompt}])
        db.increment_metric("offers_sent")
        return response.content
    except Exception as e:
        logger.error("Document generation failed: %s", e)
        return f"Failed to generate {document_type}: {str(e)}"


@tool
def verify_candidate_links(candidate_name: str) -> str:
    """Verify the authenticity of links found in a candidate's resume by crawling each URL and analyzing the page content. Returns a verification report with per-link verdicts (verified/unverified/inconclusive/inaccessible) and an overall authenticity score."""
    # Check uploaded PDF data first
    pdf_data = db.get_uploaded_pdf(candidate_name)
    if pdf_data:
        links = pdf_data.get("links", [])
        resume_text = pdf_data.get("text", "")
    else:
        # Check sample resumes
        for r in db.get_sample_resumes():
            if r["name"].lower() == candidate_name.lower():
                links = r.get("links", [])
                resume_text = r.get("resume_text", "")
                break
        else:
            return f"No resume data found for '{candidate_name}'. Please upload their resume first."

    if not links:
        return f"No links found in {candidate_name}'s resume to verify."

    report = _verify_links(candidate_name, links, resume_text)
    db.store_verification_report(report)
    db.increment_metric("verifications_completed")

    # Format output
    lines = [f"🔍 Verification Report for {report.candidate_name}", ""]
    for lv in report.links:
        icon = {"verified": "✅", "unverified": "❌", "inconclusive": "❓", "inaccessible": "🚫"}.get(lv.verdict, "❓")
        lines.append(f"  {icon} [{lv.verdict.upper()}] {lv.url}")
        lines.append(f"     {lv.reasoning}")
        lines.append("")
    lines.append(f"Overall Authenticity Score: {report.overall_score}/100")
    lines.append(report.summary)
    return "\n".join(lines)


@tool
def list_sample_resumes() -> str:
    """List all sample resumes available in the database with candidate names and key details."""
    resumes = db.get_sample_resumes()
    lines = ["📄 Available Sample Resumes:", ""]
    for r in resumes:
        lines.append(f"  • {r['name']} — {r['skills'][:3]} — {r['years_of_experience']} yrs exp")
        lines.append(f"    Email: {r['email']}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

def get_all_tools() -> list:
    """Return all available HR tools for the LangChain agent."""
    return [
        resume_parser,
        job_description_parser,
        candidate_matcher,
        schedule_interview,
        send_email,
        update_onboarding,
        get_onboarding_status,
        leave_manager,
        check_leave_balance,
        policy_search,
        generate_document,
        verify_candidate_links,
        list_sample_resumes,
    ]
