"""
LLM-powered resume text parser.
Extracts structured candidate information from raw resume text.
"""

from __future__ import annotations

import json
import logging

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert HR resume parser. Given raw resume text, extract structured information.

Return ONLY valid JSON with these fields:
{
  "name": "Full Name",
  "email": "email@example.com",
  "education": ["Degree, Institution"],
  "skills": ["skill1", "skill2"],
  "previous_roles": ["Role at Company (duration)"],
  "years_of_experience": 0.0,
  "links": ["https://..."]
}

Extract all URLs/links found in the resume (GitHub, LinkedIn, portfolio, certification links, etc).
If a field cannot be determined, use an empty string or empty list.
Be thorough and domain-agnostic — work with resumes from any industry."""


def resume_parser(resume_text: str) -> str:
    """Parse resume text and extract structured candidate information.

    Args:
        resume_text: Raw resume text content.

    Returns:
        JSON string with structured candidate data.
    """
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        response = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse this resume:\n\n{resume_text}"},
        ])
        result = response.content.strip()
        # Strip markdown code fences if present
        if result.startswith("```"):
            result = result.split("\n", 1)[1] if "\n" in result else result[3:]
            if result.endswith("```"):
                result = result[:-3]
        # Validate JSON
        json.loads(result)
        return result
    except Exception as e:
        logger.error("Resume parsing failed: %s", e)
        return json.dumps({
            "error": f"Failed to parse resume: {str(e)}",
            "name": "", "email": "", "education": [],
            "skills": [], "previous_roles": [],
            "years_of_experience": 0, "links": []
        })
