"""
FastAPI server for the Universal HR Autonomous Agent.
Implements A2A JSON-RPC 2.0 protocol, PDF resume upload, and metrics endpoints.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .agent import process_message
from .database import (
    get_metrics,
    increment_metric,
    store_uploaded_pdf,
    store_candidate,
)
from .models import (
    A2AArtifact,
    A2APart,
    A2AResult,
    A2ATask,
    CandidateProfile,
    TaskStatus,
)
from .job_parser import job_description_parser
from .matcher import candidate_matcher
from .resume_parser import resume_parser
from .resume_pdf_parser import extract_links_from_pdf, extract_text_from_pdf
from .verification_agent import verify_resume_links

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Universal HR Autonomous Agent",
    description="AI-powered HR operations agent supporting the A2A JSON-RPC protocol",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Agent Card
# ---------------------------------------------------------------------------

AGENT_CARD = {
    "name": "Universal HR Autonomous Agent",
    "description": (
        "An industry-agnostic AI HR operations agent capable of automating "
        "recruitment screening, candidate evaluation, interview scheduling, "
        "onboarding management, leave processing, HR policy assistance, "
        "document generation, and resume link verification."
    ),
    "url": "http://localhost:5000",
    "version": "1.0.0",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
    },
    "skills": [
        {
            "id": "resume_parsing",
            "name": "Resume Parsing",
            "description": "Parse resumes from text or PDF to extract structured candidate data",
        },
        {
            "id": "job_matching",
            "name": "Job Matching",
            "description": "Match candidates to job descriptions with scored reasoning",
        },
        {
            "id": "interview_scheduling",
            "name": "Interview Scheduling",
            "description": "Schedule and manage candidate interviews",
        },
        {
            "id": "onboarding",
            "name": "Onboarding Management",
            "description": "Track and manage employee onboarding checklists",
        },
        {
            "id": "leave_management",
            "name": "Leave Management",
            "description": "Process leave requests and check balances",
        },
        {
            "id": "policy_helpdesk",
            "name": "HR Policy Helpdesk",
            "description": "Answer questions about HR policies",
        },
        {
            "id": "document_generation",
            "name": "HR Document Generation",
            "description": "Generate offer letters, confirmations, and other HR documents",
        },
        {
            "id": "link_verification",
            "name": "Resume Link Verification",
            "description": "Crawl and verify links in resumes for project/certification authenticity",
        },
    ],
    "defaultInputModes": ["text"],
    "defaultOutputModes": ["text"],
    "provider": {
        "organization": "Nasiko AI",
        "url": "https://nasiko.ai",
    },
    "protocolVersion": "0.1",
}


# ---------------------------------------------------------------------------
# A2A JSON-RPC Endpoint
# ---------------------------------------------------------------------------

@app.post("/")
async def a2a_endpoint(request: dict):
    """Handle A2A JSON-RPC 2.0 requests.

    Supports the `message/send` method.
    """
    jsonrpc = request.get("jsonrpc", "")
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    if jsonrpc != "2.0":
        return JSONResponse(
            content=A2AResult(
                id=req_id,
                error={"code": -32600, "message": "Invalid JSON-RPC version"},
            ).model_dump(),
            status_code=400,
        )

    if method != "message/send":
        return JSONResponse(
            content=A2AResult(
                id=req_id,
                error={"code": -32601, "message": f"Method '{method}' not found"},
            ).model_dump(),
            status_code=404,
        )

    try:
        message = params.get("message", {})
        parts = message.get("parts", [])
        user_text = " ".join(
            p.get("text", "") for p in parts if p.get("type") == "text"
        ).strip()

        if not user_text:
            return JSONResponse(
                content=A2AResult(
                    id=req_id,
                    error={"code": -32602, "message": "No text content in message"},
                ).model_dump(),
                status_code=400,
            )

        logger.info("A2A request: %s", user_text[:100])

        # Process through the agent
        response_text = process_message(user_text)

        task = A2ATask(
            id=str(uuid.uuid4()),
            status=TaskStatus.COMPLETED,
            artifacts=[
                A2AArtifact(
                    name="response",
                    parts=[A2APart(type="text", text=response_text)],
                )
            ],
        )

        return JSONResponse(
            content=A2AResult(id=req_id, result=task).model_dump(),
        )

    except Exception as e:
        logger.error("A2A processing error: %s", e, exc_info=True)
        return JSONResponse(
            content=A2AResult(
                id=req_id,
                error={"code": -32603, "message": f"Internal error: {str(e)}"},
            ).model_dump(),
            status_code=500,
        )


# ---------------------------------------------------------------------------
# PDF Resume Upload Endpoint
# ---------------------------------------------------------------------------

@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    job_role: str | None = Form(None),
):
    """Upload a PDF resume for parsing, storage, link verification, and optional job matching.

    Accepts a multipart file upload, extracts text and links from the PDF,
    parses candidate information via LLM, stores everything in the database,
    and triggers the verification sub-agent on any links found.

    When a ``job_role`` is provided, the candidate is also matched and scored
    against the job requirements so the hiring team gets an instant fit report.

    Returns:
        JSON with parsed candidate data, extracted links, verification report,
        and (when job_role is given) a job_match score with reasoning.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    try:
        pdf_bytes = await file.read()
        logger.info("Received PDF upload: %s (%d bytes)", file.filename, len(pdf_bytes))

        # Save file
        save_path = UPLOAD_DIR / file.filename
        save_path.write_bytes(pdf_bytes)

        # Extract text and links
        text = extract_text_from_pdf(pdf_bytes)
        links = extract_links_from_pdf(pdf_bytes)

        if not text:
            raise HTTPException(
                status_code=422,
                detail="Could not extract text from the PDF. The file may be image-based or corrupted.",
            )

        # Parse resume with LLM
        parsed_json = resume_parser(text)
        parsed_data = json.loads(parsed_json)

        # Merge extracted links with parsed links
        all_links = list(set(links + parsed_data.get("links", [])))
        parsed_data["links"] = all_links

        candidate_name = parsed_data.get("name", "Unknown")

        # Store in database
        store_uploaded_pdf(candidate_name, text, all_links)
        profile = CandidateProfile(
            name=candidate_name,
            email=parsed_data.get("email", ""),
            education=parsed_data.get("education", []),
            skills=parsed_data.get("skills", []),
            previous_roles=parsed_data.get("previous_roles", []),
            years_of_experience=parsed_data.get("years_of_experience", 0),
            links=all_links,
            resume_text=text,
        )
        store_candidate(profile)
        increment_metric("resumes_screened")
        increment_metric("resumes_uploaded")

        # Run verification agent on links
        verification_result = None
        if all_links:
            logger.info("Running verification agent on %d links for %s", len(all_links), candidate_name)
            report = verify_resume_links(candidate_name, all_links, text)
            verification_result = report.model_dump()

        # -- Job role matching (when provided) --------------------------------
        job_match_result = None
        if job_role:
            logger.info("Matching %s against job role: %s", candidate_name, job_role[:80])
            job_requirements_json = job_description_parser(job_role)
            match_json = candidate_matcher(
                candidate_profile=json.dumps(parsed_data),
                job_requirements=job_requirements_json,
            )
            job_match_result = json.loads(match_json)
            increment_metric("candidates_matched")

        response_payload: dict = {
            "status": "success",
            "filename": file.filename,
            "candidate": parsed_data,
            "links_found": all_links,
            "verification_report": verification_result,
        }
        if job_role:
            response_payload["job_role"] = job_role
            response_payload["job_match"] = job_match_result

        return JSONResponse(content=response_payload)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Resume upload failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Resume processing failed: {str(e)}")


# ---------------------------------------------------------------------------
# Metrics Endpoint
# ---------------------------------------------------------------------------

@app.get("/hr-metrics")
async def hr_metrics():
    """Return HR dashboard metrics."""
    metrics = get_metrics()
    return JSONResponse(content=metrics.model_dump())


# ---------------------------------------------------------------------------
# Agent Card Endpoint
# ---------------------------------------------------------------------------

@app.get("/agent-card")
async def agent_card():
    """Return the A2A Agent Card."""
    return JSONResponse(content=AGENT_CARD)


@app.get("/.well-known/agent.json")
async def well_known_agent_card():
    """A2A standard well-known endpoint for agent discovery."""
    return JSONResponse(content=AGENT_CARD)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse(content={"status": "healthy", "agent": "Universal HR Autonomous Agent"})


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "5000"))
    logger.info("Starting Universal HR Agent on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
