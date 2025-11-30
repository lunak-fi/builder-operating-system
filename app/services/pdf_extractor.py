import pdfplumber
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PDFExtractionError(Exception):
    """Raised when PDF extraction fails"""
    pass


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file using pdfplumber.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text as a string

    Raises:
        PDFExtractionError: If extraction fails
    """
    try:
        # Verify file exists
        if not Path(file_path).exists():
            raise PDFExtractionError(f"File not found: {file_path}")

        # Verify it's a PDF
        if not file_path.lower().endswith('.pdf'):
            raise PDFExtractionError(f"File is not a PDF: {file_path}")

        extracted_text = []

        with pdfplumber.open(file_path) as pdf:
            # Check if PDF is empty
            if len(pdf.pages) == 0:
                raise PDFExtractionError("PDF has no pages")

            logger.info(f"Extracting text from {len(pdf.pages)} pages")

            # Extract text from each page
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text()
                    if text:
                        extracted_text.append(f"--- Page {page_num} ---\n{text}")
                    else:
                        logger.warning(f"Page {page_num} has no extractable text (may be scanned)")
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
                    continue

        if not extracted_text:
            raise PDFExtractionError("No text could be extracted from PDF (may be scanned or image-based)")

        full_text = "\n\n".join(extracted_text)
        logger.info(f"Successfully extracted {len(full_text)} characters from PDF")

        return full_text

    except pdfplumber.pdfminer.pdfparser.PDFSyntaxError as e:
        raise PDFExtractionError(f"Invalid or corrupted PDF file: {str(e)}")
    except Exception as e:
        if isinstance(e, PDFExtractionError):
            raise
        raise PDFExtractionError(f"Unexpected error during extraction: {str(e)}")


def extract_text_with_metadata(file_path: str) -> dict:
    """
    Extract text and metadata from PDF.

    Args:
        file_path: Path to the PDF file

    Returns:
        Dictionary with text, metadata, and page count
    """
    try:
        metadata = {
            "text": None,
            "page_count": 0,
            "file_size_bytes": 0,
            "has_images": False,
            "error": None
        }

        # Get file size
        file_path_obj = Path(file_path)
        metadata["file_size_bytes"] = file_path_obj.stat().st_size

        with pdfplumber.open(file_path) as pdf:
            metadata["page_count"] = len(pdf.pages)

            # Check for images (basic check)
            for page in pdf.pages:
                if len(page.images) > 0:
                    metadata["has_images"] = True
                    break

        # Extract text
        metadata["text"] = extract_text_from_pdf(file_path)

        return metadata

    except PDFExtractionError as e:
        return {
            "text": None,
            "page_count": 0,
            "file_size_bytes": 0,
            "has_images": False,
            "error": str(e)
        }
    except Exception as e:
        return {
            "text": None,
            "page_count": 0,
            "file_size_bytes": 0,
            "has_images": False,
            "error": f"Unexpected error: {str(e)}"
        }
