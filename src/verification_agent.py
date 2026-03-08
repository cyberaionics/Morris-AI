"""
Verification Sub-Agent.
Autonomously crawls URLs found in resumes to verify project and certification claims.
Produces a structured verification report with per-link verdicts and an overall score.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI

from .models import LinkVerification, VerificationReport

logger = logging.getLogger(__name__)

# Maximum characters to send to LLM from a crawled page
MAX_PAGE_CHARS = 3000

# Timeout for HTTP requests (seconds)
REQUEST_TIMEOUT = 15


# ---------------------------------------------------------------------------
# URL Crawling
# ---------------------------------------------------------------------------

async def crawl_url(url: str) -> dict[str, Any]:
    """Fetch a URL and return cleaned text content.

    Args:
        url: The URL to crawl.

    Returns:
        Dict with 'success', 'text', and 'error' fields.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; HRVerificationBot/1.0; "
            "+https://example.com/hr-agent)"
        )
    }
    try:
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True, ssl=False) as resp:
                if resp.status != 200:
                    return {
                        "success": False,
                        "text": "",
                        "error": f"HTTP {resp.status}",
                    }
                html = await resp.text(errors="replace")
                soup = BeautifulSoup(html, "html.parser")

                # Remove script and style elements
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()

                text = soup.get_text(separator="\n", strip=True)
                # Truncate to manageable size
                text = text[:MAX_PAGE_CHARS]
                return {"success": True, "text": text, "error": ""}
    except asyncio.TimeoutError:
        return {"success": False, "text": "", "error": "Request timed out"}
    except Exception as e:
        logger.warning("Failed to crawl %s: %s", url, e)
        return {"success": False, "text": "", "error": str(e)}


# ---------------------------------------------------------------------------
# Single Link Verification via LLM
# ---------------------------------------------------------------------------

VERIFY_PROMPT = """You are an HR verification specialist. Analyze whether a web page supports a candidate's resume claims.

Candidate: {candidate_name}
Resume Summary: {resume_summary}
URL: {url}

Page Content:
---
{page_content}
---

Evaluate:
1. Does this page belong to or reference the candidate?
2. Does the content support claims in their resume (projects, skills, certifications)?
3. Are there any red flags or inconsistencies?

Return ONLY valid JSON:
{{
  "verdict": "verified" | "unverified" | "inconclusive",
  "confidence": 0-100,
  "reasoning": "Brief explanation"
}}"""


def verify_single_link(
    url: str,
    candidate_name: str,
    resume_summary: str,
    page_content: str,
) -> LinkVerification:
    """Use LLM to verify whether a crawled page supports the candidate's claims.

    Args:
        url: The URL being verified.
        candidate_name: Name of the candidate.
        resume_summary: Summary of the candidate's resume.
        page_content: Text extracted from the web page.

    Returns:
        LinkVerification with verdict and reasoning.
    """
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        prompt = VERIFY_PROMPT.format(
            candidate_name=candidate_name,
            resume_summary=resume_summary,
            url=url,
            page_content=page_content,
        )
        response = llm.invoke([{"role": "user", "content": prompt}])
        result = response.content.strip()

        # Strip markdown code fences if present
        if result.startswith("```"):
            result = result.split("\n", 1)[1] if "\n" in result else result[3:]
            if result.endswith("```"):
                result = result[:-3]

        data = json.loads(result)
        return LinkVerification(
            url=url,
            verdict=data.get("verdict", "inconclusive"),
            reasoning=data.get("reasoning", "No reasoning provided."),
        )
    except Exception as e:
        logger.error("LLM verification failed for %s: %s", url, e)
        return LinkVerification(
            url=url,
            verdict="inconclusive",
            reasoning=f"Verification error: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Full Resume Link Verification
# ---------------------------------------------------------------------------

async def _crawl_all(urls: list[str]) -> list[dict[str, Any]]:
    """Crawl multiple URLs concurrently."""
    tasks = [crawl_url(url) for url in urls]
    return await asyncio.gather(*tasks)


def verify_resume_links(
    candidate_name: str,
    links: list[str],
    resume_summary: str,
) -> VerificationReport:
    """Orchestrate verification of all links from a candidate's resume.

    Crawls each URL, analyzes the page content via LLM, and produces
    a structured report with per-link verdicts and an overall score.

    Args:
        candidate_name: Name of the candidate.
        links: List of URLs extracted from their resume.
        resume_summary: Summary/text of the candidate's resume for context.

    Returns:
        VerificationReport with per-link results and an overall score.
    """
    if not links:
        return VerificationReport(
            candidate_name=candidate_name,
            links=[],
            overall_score=0,
            summary="No links found in the resume to verify.",
        )

    logger.info("Starting verification of %d links for %s", len(links), candidate_name)

    # Crawl all URLs
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're inside an async context (e.g. FastAPI)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                crawl_results = pool.submit(
                    asyncio.run, _crawl_all(links)
                ).result()
        else:
            crawl_results = asyncio.run(_crawl_all(links))
    except RuntimeError:
        crawl_results = asyncio.run(_crawl_all(links))

    # Verify each link
    verifications: list[LinkVerification] = []
    for url, crawl_result in zip(links, crawl_results):
        if not crawl_result["success"]:
            verifications.append(LinkVerification(
                url=url,
                verdict="inaccessible",
                reasoning=f"Could not access URL: {crawl_result['error']}",
            ))
            continue

        verification = verify_single_link(
            url=url,
            candidate_name=candidate_name,
            resume_summary=resume_summary,
            page_content=crawl_result["text"],
        )
        verifications.append(verification)

    # Calculate overall score
    if verifications:
        verdict_scores = {
            "verified": 100,
            "inconclusive": 50,
            "unverified": 10,
            "inaccessible": 30,
        }
        total = sum(
            verdict_scores.get(v.verdict, 50) for v in verifications
        )
        overall_score = total // len(verifications)
    else:
        overall_score = 0

    # Generate summary
    verified_count = sum(1 for v in verifications if v.verdict == "verified")
    unverified_count = sum(1 for v in verifications if v.verdict == "unverified")
    inconclusive_count = sum(1 for v in verifications if v.verdict == "inconclusive")
    inaccessible_count = sum(1 for v in verifications if v.verdict == "inaccessible")

    summary = (
        f"Verification complete for {candidate_name}. "
        f"Checked {len(verifications)} link(s): "
        f"{verified_count} verified, {unverified_count} unverified, "
        f"{inconclusive_count} inconclusive, {inaccessible_count} inaccessible. "
        f"Overall authenticity score: {overall_score}/100."
    )

    report = VerificationReport(
        candidate_name=candidate_name,
        links=verifications,
        overall_score=overall_score,
        summary=summary,
    )

    logger.info("Verification report: %s", summary)
    return report
