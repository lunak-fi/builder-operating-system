import pdfplumber
import logging
from pathlib import Path
from typing import Optional, List, Tuple
from pdf2image import convert_from_path
from PIL import Image
import io
import base64

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


def extract_key_pages_as_images(
    pdf_path: str,
    page_numbers: List[int] = None,
    max_pages: int = 4,
    max_width: int = 1536
) -> List[Tuple[int, str, str]]:
    """
    Extract specific PDF pages as base64-encoded images.

    Args:
        pdf_path: Path to PDF file
        page_numbers: Specific pages to extract (1-indexed). If None, extracts first max_pages
        max_pages: Maximum number of pages to extract
        max_width: Max width in pixels (images are downscaled to save tokens)

    Returns:
        List of tuples: [(page_num, media_type, base64_data), ...]

    Raises:
        PDFExtractionError: If image extraction fails
    """
    try:
        if not Path(pdf_path).exists():
            raise PDFExtractionError(f"File not found: {pdf_path}")

        logger.info(f"Converting PDF pages to images: {pdf_path}")

        # Convert PDF pages to PIL images
        # DPI 150 is good balance between quality and size
        images = convert_from_path(
            pdf_path,
            dpi=150,
            fmt='png',
            thread_count=2
        )

        # Determine which pages to extract
        if page_numbers is None:
            # Default: first N pages (usually cover + summary pages)
            page_numbers = list(range(1, min(len(images) + 1, max_pages + 1)))

        # Limit to max_pages
        page_numbers = page_numbers[:max_pages]

        result = []
        for page_num in page_numbers:
            if page_num < 1 or page_num > len(images):
                logger.warning(f"Page {page_num} out of range (1-{len(images)})")
                continue

            # Get image (0-indexed)
            img = images[page_num - 1]

            # Downscale if needed to save tokens
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Downscaled page {page_num} to {max_width}x{new_height}")

            # Convert to PNG bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG', optimize=True)
            img_bytes.seek(0)

            # Base64 encode
            img_base64 = base64.b64encode(img_bytes.read()).decode('utf-8')

            result.append((page_num, "image/png", img_base64))
            logger.info(f"Extracted page {page_num} as image ({len(img_base64)} base64 chars)")

        if not result:
            raise PDFExtractionError("No pages could be converted to images")

        return result

    except Exception as e:
        if isinstance(e, PDFExtractionError):
            raise
        raise PDFExtractionError(f"Image extraction failed: {str(e)}")


def identify_financial_pages(pdf_text: str, total_pages: int) -> List[int]:
    """
    Identify which pages likely contain financial metrics based on section headers and keywords.

    Args:
        pdf_text: Extracted text with page markers
        total_pages: Total number of pages in PDF

    Returns:
        List of page numbers (1-indexed) likely containing financial data
    """
    # Split by page markers
    pages = pdf_text.split("--- Page ")

    # Priority headers - pages with these titles are almost certainly key pages
    # These typically appear at the top of the page or as section headers
    priority_headers = [
        'financial summary', 'deal metrics', 'investment summary',
        'financial analysis', 'sources and uses', 'sources & uses',
        'project summary', 'capital stack', 'investment highlights',
        'key metrics', 'projected returns', 'underwriting summary'
    ]

    # Secondary keywords - need multiple matches to qualify
    secondary_keywords = [
        'irr', 'equity multiple', 'moic', 'dscr', 'cap rate',
        'total raise', 'sponsor equity', 'lp equity',
        'purchase price', 'acquisition price', 'total cost',
        'cash flow', 'proforma', 'pro forma', 'noi', 'yield'
    ]

    priority_pages = set()
    secondary_pages = set()

    for i, page_text in enumerate(pages[1:], start=1):  # Skip first split (before any page)
        page_text_lower = page_text.lower()

        # Check for priority headers (single match = high confidence)
        for header in priority_headers:
            if header in page_text_lower:
                priority_pages.add(i)
                logger.info(f"Page {i} matched priority header: '{header}'")
                break

        # Check for secondary keywords (need 2+ matches)
        if i not in priority_pages:
            keyword_count = sum(1 for kw in secondary_keywords if kw in page_text_lower)
            if keyword_count >= 2:
                secondary_pages.add(i)

    # Always include page 1 (cover/summary)
    priority_pages.add(1)

    # Combine: priority pages first, then secondary pages
    result = sorted(list(priority_pages)) + sorted(list(secondary_pages - priority_pages))

    logger.info(f"Identified financial pages: {result} (priority: {sorted(priority_pages)}, secondary: {sorted(secondary_pages)})")

    return result
