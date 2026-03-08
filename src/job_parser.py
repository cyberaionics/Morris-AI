"""
LLM-powered job description parser.
Extracts structured requirements from any job description text.
"""

from __future__ import annotations

import json
import logging

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert HR analyst. Given a job description, extract structured requirements.

Return ONLY valid JSON with these fields:
{
  "title": "Job Title",
  "required_skills": ["skill1", "skill2"],
  "responsibilities": ["responsibility1", "responsibility2"],
  "experience_level": "junior/mid/senior/manager/director",
  "domain": "technology/finance/healthcare/marketing/manufacturing/other",
  "education_requirements": ["Degree requirement"]
}

Be thorough. Extract all relevant skills, including both technical and soft skills.
Infer the domain from context if not explicitly stated."""


def job_description_parser(job_description: str) -> str:
    """Parse a job description and extract structured requirements.

    Args:
        job_description: Raw job description text.

    Returns:
        JSON string with structured job requirements.
    """
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        response = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse this job description:\n\n{job_description}"},
        ])
        result = response.content.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1] if "\n" in result else result[3:]
            if result.endswith("```"):
                result = result[:-3]
        json.loads(result)
        return result
    except Exception as e:
        logger.error("Job description parsing failed: %s", e)
        return json.dumps({
            "error": f"Failed to parse job description: {str(e)}",
            "title": "", "required_skills": [], "responsibilities": [],
            "experience_level": "", "domain": "", "education_requirements": []
        })
