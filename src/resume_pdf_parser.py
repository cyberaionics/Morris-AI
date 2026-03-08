"""
PDF Resume Parser.
Extracts text and hyperlinks from uploaded PDF resume files using PyMuPDF.
"""

from __future__ import annotations

import logging
import re

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Common URL pattern for extraction from text
URL_PATTERN = re.compile(
    r'https?://[^\s<>"\')\],;]+',
    re.IGNORECASE,
)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text content from a PDF file.

    Args:
        pdf_bytes: Raw bytes of the PDF file.

    Returns:
        Concatenated text from all pages.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages: list[str] = []
        for page in doc:
            text = page.get_text("text")
            if text:
                pages.append(text.strip())
        doc.close()
        full_text = "\n\n".join(pages)
        logger.info("Extracted %d characters from %d-page PDF", len(full_text), len(pages))
        return full_text
    except Exception as e:
        logger.error("PDF text extraction failed: %s", e)
        return ""


def extract_links_from_pdf(pdf_bytes: bytes) -> list[str]:
    """Extract all unique hyperlinks from a PDF file.

    Extracts links from both PDF annotations (clickable links) and
    from the raw text using URL pattern matching.

    Args:
        pdf_bytes: Raw bytes of the PDF file.

    Returns:
        Deduplicated list of URLs found in the PDF.
    """
    links: set[str] = set()
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            # Method 1: Extract from PDF link annotations
            for link in page.get_links():
                uri = link.get("uri", "")
                if uri and uri.startswith("http"):
                    links.add(uri.rstrip("/"))

            # Method 2: Extract URLs from text content
            text = page.get_text("text")
            for match in URL_PATTERN.findall(text):
                links.add(match.rstrip("/").rstrip(".").rstrip(","))

        doc.close()
        result = sorted(links)
        logger.info("Extracted %d unique links from PDF", len(result))
        return result
    except Exception as e:
        logger.error("PDF link extraction failed: %s", e)
        return []
