"""
Candidate-Job matcher.
Computes a compatibility score (0-100) with explainable reasoning.
"""

from __future__ import annotations

import json
import logging

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert HR recruiter evaluating a candidate's fit for a job.

Given a candidate profile and job requirements, provide:
1. A compatibility score from 0 to 100
2. Detailed reasoning explaining the score

Return ONLY valid JSON:
{
  "candidate_name": "Name",
  "score": 85,
  "reasoning": [
    "Strong match on required skills X, Y, Z",
    "5 years experience exceeds the 3 year requirement",
    "Missing skill A could be a gap"
  ]
}

Be fair, thorough, and domain-agnostic in your evaluation.
Consider skills overlap, experience relevance, education fit, and domain alignment."""


def candidate_matcher(candidate_profile: str, job_requirements: str) -> str:
    """Compute candidate-job compatibility score with reasoning.

    Args:
        candidate_profile: JSON or text describing the candidate.
        job_requirements: JSON or text describing the job requirements.

    Returns:
        JSON string with score (0-100) and reasoning.
    """
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        prompt = (
            f"Evaluate this candidate against the job requirements.\n\n"
            f"CANDIDATE PROFILE:\n{candidate_profile}\n\n"
            f"JOB REQUIREMENTS:\n{job_requirements}"
        )
        response = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
        result = response.content.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1] if "\n" in result else result[3:]
            if result.endswith("```"):
                result = result[:-3]
        json.loads(result)
        return result
    except Exception as e:
        logger.error("Candidate matching failed: %s", e)
        return json.dumps({
            "error": f"Matching failed: {str(e)}",
            "candidate_name": "Unknown",
            "score": 0,
            "reasoning": ["Matching could not be completed due to an error."]
        })
