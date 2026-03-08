"""
Pydantic models for the Universal HR Autonomous Agent.
Defines data structures for candidates, jobs, interviews, leave, onboarding,
HR metrics, and A2A protocol envelopes.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# HR Domain Models
# ---------------------------------------------------------------------------

class CandidateProfile(BaseModel):
    """Structured candidate information extracted from a resume."""
    name: str = ""
    email: str = ""
    education: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    previous_roles: list[str] = Field(default_factory=list)
    years_of_experience: float = 0.0
    links: list[str] = Field(default_factory=list, description="URLs found in the resume (GitHub, LinkedIn, portfolio, certs)")
    resume_text: str = ""


class JobRequirements(BaseModel):
    """Structured job requirements extracted from a job description."""
    title: str = ""
    required_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    experience_level: str = ""
    domain: str = ""
    education_requirements: list[str] = Field(default_factory=list)


class CandidateScore(BaseModel):
    """Candidate-job compatibility score with reasoning."""
    candidate_name: str
    score: int = Field(ge=0, le=100)
    reasoning: list[str] = Field(default_factory=list)


class InterviewSlot(BaseModel):
    """Scheduled interview record."""
    interview_time: datetime
    candidate_email: str
    interviewer_email: str
    status: str = "scheduled"


class LeaveRecord(BaseModel):
    """Employee leave balance and request tracking."""
    employee_name: str
    total_days: int = 24
    used_days: int = 0
    pending_requests: int = 0

    @property
    def balance(self) -> int:
        return self.total_days - self.used_days


class OnboardingTask(BaseModel):
    """Individual onboarding checklist item."""
    employee_name: str
    task_name: str
    completed: bool = False


class LinkVerification(BaseModel):
    """Verification result for a single URL from a resume."""
    url: str
    verdict: str = "pending"  # verified | unverified | inconclusive | inaccessible
    reasoning: str = ""


class VerificationReport(BaseModel):
    """Full verification report for a candidate's resume links."""
    candidate_name: str
    links: list[LinkVerification] = Field(default_factory=list)
    overall_score: int = Field(default=0, ge=0, le=100)
    summary: str = ""


class HRMetrics(BaseModel):
    """Aggregate HR dashboard metrics."""
    resumes_screened: int = 0
    candidates_shortlisted: int = 0
    interviews_scheduled: int = 0
    offers_sent: int = 0
    resumes_uploaded: int = 0
    verifications_completed: int = 0


# ---------------------------------------------------------------------------
# A2A Protocol Models  (JSON-RPC 2.0 subset)
# ---------------------------------------------------------------------------

class A2APart(BaseModel):
    type: str = "text"
    text: str = ""


class A2AMessage(BaseModel):
    role: str = "user"
    parts: list[A2APart] = Field(default_factory=list)


class A2AArtifact(BaseModel):
    name: str = "response"
    parts: list[A2APart] = Field(default_factory=list)


class TaskStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    IN_PROGRESS = "in-progress"


class A2ATask(BaseModel):
    id: str
    status: TaskStatus = TaskStatus.COMPLETED
    artifacts: list[A2AArtifact] = Field(default_factory=list)


class A2AResult(BaseModel):
    """Wraps the full JSON-RPC response."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[A2ATask] = None
    error: Optional[dict[str, Any]] = None
