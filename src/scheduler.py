"""
Interview scheduling service.
Generates interview time slots and records them in the database.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from .database import increment_metric, store_interview
from .models import InterviewSlot

logger = logging.getLogger(__name__)

# Simulated available slots start from tomorrow, one per hour from 9 AM
_slot_counter = 0


def schedule_interview(candidate_email: str, interviewer_email: str) -> str:
    """Schedule an interview between a candidate and interviewer.

    Finds the next available interview slot and records it.

    Args:
        candidate_email: Email address of the candidate.
        interviewer_email: Email address of the interviewer.

    Returns:
        Confirmation string with the scheduled time.
    """
    global _slot_counter
    try:
        # Generate a slot: tomorrow + offset hours
        base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        base += timedelta(days=1)  # Start from tomorrow
        interview_time = base + timedelta(hours=_slot_counter)

        # Ensure within business hours (9 AM - 5 PM)
        hour = interview_time.hour
        if hour >= 17:
            # Roll to next day
            days_forward = (hour - 9) // 8 + 1
            interview_time = base + timedelta(days=days_forward)
            interview_time = interview_time.replace(hour=9 + (_slot_counter % 8))

        _slot_counter += 1

        slot = InterviewSlot(
            interview_time=interview_time,
            candidate_email=candidate_email,
            interviewer_email=interviewer_email,
            status="scheduled",
        )
        store_interview(slot)
        increment_metric("interviews_scheduled")

        formatted_time = interview_time.strftime("%A, %B %d, %Y at %I:%M %p")
        result = (
            f"✅ Interview Scheduled\n"
            f"  Candidate: {candidate_email}\n"
            f"  Interviewer: {interviewer_email}\n"
            f"  Time: {formatted_time}\n"
            f"  Status: Confirmed"
        )
        logger.info("Interview scheduled: %s with %s at %s", candidate_email, interviewer_email, formatted_time)
        return result
    except Exception as e:
        logger.error("Failed to schedule interview: %s", e)
        return f"Failed to schedule interview: {str(e)}"
