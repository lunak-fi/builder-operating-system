import json
import logging
from typing import Dict, Any, Optional
from anthropic import Anthropic
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class LLMSettings(BaseSettings):
    anthropic_api_key: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class LLMExtractionError(Exception):
    """Raised when LLM extraction fails"""
    pass


def extract_deal_data_from_text(pdf_text: str) -> Dict[str, Any]:
    """
    Extract structured deal data from PDF text using Claude AI.

    Args:
        pdf_text: Raw text extracted from PDF

    Returns:
        Dictionary with extracted structured data:
        {
            "operator": {...},
            "deal": {...},
            "principals": [...],
            "underwriting": {...}
        }

    Raises:
        LLMExtractionError: If extraction fails
    """
    try:
        # Initialize Anthropic client
        settings = LLMSettings()
        client = Anthropic(
            api_key=settings.anthropic_api_key,
            max_retries=2
        )

        # Construct extraction prompt
        extraction_prompt = _build_extraction_prompt(pdf_text)

        logger.info("Sending extraction request to Claude API")

        # Call Claude API
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": extraction_prompt
                }
            ]
        )

        # Extract JSON from response
        response_text = message.content[0].text
        logger.info(f"Received response from Claude API ({len(response_text)} chars)")

        # Parse JSON response
        extracted_data = _parse_extraction_response(response_text)

        logger.info("Successfully extracted structured data from PDF text")
        return extracted_data

    except Exception as e:
        if isinstance(e, LLMExtractionError):
            raise
        raise LLMExtractionError(f"Unexpected error during LLM extraction: {str(e)}")


def extract_deal_data_from_vision(
    pdf_path: str,
    text_fallback: str = None
) -> Dict[str, Any]:
    """
    Extract structured deal data from PDF using Claude Vision.

    Intelligently selects 2-4 key pages to send as images based on content.

    Args:
        pdf_path: Path to PDF file
        text_fallback: Optional extracted text for identifying key pages

    Returns:
        Dictionary with extracted structured data (same format as text extraction)

    Raises:
        LLMExtractionError: If extraction fails
    """
    try:
        from app.services.pdf_extractor import (
            extract_key_pages_as_images,
            identify_financial_pages,
            PDFExtractionError
        )
        import pdfplumber

        # Identify which pages to extract as images
        page_numbers = None
        if text_fallback:
            # Use text hints to find financial pages
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
            page_numbers = identify_financial_pages(text_fallback, total_pages)

        # Extract key pages as images (limit to 4 pages max)
        logger.info(f"Extracting PDF pages as images: {pdf_path}")
        images = extract_key_pages_as_images(
            pdf_path,
            page_numbers=page_numbers,
            max_pages=4,
            max_width=1536  # Good balance between quality and tokens
        )

        # Build message content with images + text prompt
        content = []

        # Add all images first
        for page_num, media_type, base64_data in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_data
                }
            })

        # Add text extraction prompt
        extraction_prompt = _build_extraction_prompt("")  # Empty text, vision will read images

        # Add vision-specific instructions
        vision_instructions = """

IMPORTANT - VISION EXTRACTION INSTRUCTIONS:
- You are viewing PDF pages as IMAGES, not text
- Carefully read ALL visible text, tables, charts, and graphics
- Pay special attention to:
  * Financial tables and metrics (IRR, Equity Multiple, DSCR, Cap Rates)
  * Property details tables (Square Footage, Units, Address)
  * Investment summary boxes or callouts
  * Charts with labeled values
- Extract numbers EXACTLY as shown (including decimals and units)
- If metrics are in a table, read row/column headers to understand context
- Some pages may have multiple columns - read left to right, top to bottom
- CRITICAL: Focus on the PRIMARY investment opportunity (usually prominently featured)
- IGNORE any "Track Record", "Case Studies", "Past Performance", or "Realized Deals" sections
- Extract data for the CURRENT deal being offered, NOT historical completed deals"""

        content.append({
            "type": "text",
            "text": extraction_prompt + vision_instructions
        })

        # Initialize Anthropic client
        settings = LLMSettings()
        client = Anthropic(
            api_key=settings.anthropic_api_key,
            max_retries=2
        )

        logger.info(f"Sending vision extraction request to Claude API ({len(images)} images)")

        # Call Claude Vision API
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ]
        )

        # Extract JSON from response (same as text extraction)
        response_text = message.content[0].text
        logger.info(f"Received vision response from Claude API ({len(response_text)} chars)")
        logger.info(f"Token usage: {message.usage.input_tokens} input, {message.usage.output_tokens} output")

        # Parse JSON response (reuse existing function)
        extracted_data = _parse_extraction_response(response_text)

        logger.info("Successfully extracted structured data from PDF using vision")
        return extracted_data

    except PDFExtractionError as e:
        logger.error(f"Image extraction failed: {str(e)}")
        raise LLMExtractionError(f"Vision extraction failed (image conversion): {str(e)}")
    except Exception as e:
        if isinstance(e, LLMExtractionError):
            raise
        raise LLMExtractionError(f"Unexpected error during vision extraction: {str(e)}")


def _build_extraction_prompt(pdf_text: str) -> str:
    """
    Build the extraction prompt for Claude.

    Uses a comprehensive prompt that extracts all data in one pass.
    """
    # Increase limit to 100k chars to ensure middle pages (where metrics often are) aren't truncated
    # Example: "Streets of Chester" has all metrics on page 5 (middle of deck)
    if len(pdf_text) > 100000:
        pdf_text = pdf_text[:100000] + "\n\n[... text truncated ...]"
        logger.info(f"Truncated PDF text at 100k characters")

    prompt = f"""You are analyzing a commercial real estate investment memorandum. Extract all relevant structured data from this document.

DOCUMENT TEXT:
{pdf_text}

---

Please extract the following information and return it as valid JSON:

{{
  "operators": [
    {{
      "name": "Sponsor/operator name (required)",
      "legal_name": "Legal entity name if different (optional)",
      "website_url": "Website URL (optional)",
      "hq_city": "Headquarters city (optional)",
      "hq_state": "Headquarters state (optional)",
      "hq_country": "Headquarters country (optional)",
      "primary_geography_focus": "Primary geographic focus area (optional)",
      "primary_asset_type_focus": "Primary asset type focus (optional)",
      "description": "Brief description of the operator (optional)",
      "is_primary": "true if lead sponsor, false otherwise (boolean)"
    }}
  ],
  "deal": {{
    "deal_name": "Name of this specific deal/property (required)",
    "internal_code": "Any internal reference code (optional, generate one if not found)",
    "country": "Country where property is located (optional)",
    "state": "State where property is located (optional)",
    "msa": "Metropolitan Statistical Area (optional)",
    "submarket": "Submarket name (optional)",
    "address_line1": "Street address (optional)",
    "postal_code": "Zip/postal code (optional)",
    "asset_type": "Asset type: Multifamily, Office, Retail, Industrial, etc. (optional)",
    "strategy_type": "Investment strategy: Value-Add, Core, Core-Plus, Opportunistic, Development, etc. (optional)",
    "num_units": "Number of units (integer, optional)",
    "building_sf": "Building square footage (numeric, optional)",
    "year_built": "Year built (integer, optional)",
    "business_plan_summary": "Brief summary of business plan (optional)",
    "hold_period_years": "Expected hold period in years (integer, optional)"
  }},
  "principals": [
    {{
      "full_name": "Full name (required)",
      "headline": "Title or role (optional)",
      "linkedin_url": "LinkedIn URL (optional)",
      "email": "Email address (optional)",
      "phone": "Phone number (optional)",
      "bio": "Biography (optional)",
      "background_summary": "Brief background summary (optional)",
      "years_experience": "Years of experience (integer, optional)"
    }}
  ],
  "underwriting": {{
    "total_project_cost": "Total project/development cost (numeric, optional)",
    "land_cost": "Land acquisition/purchase price (numeric, optional)",
    "hard_cost": "Hard costs/construction costs (numeric, optional)",
    "soft_cost": "Soft costs (fees, permits, etc.) (numeric, optional)",
    "loan_amount": "Loan amount (numeric, optional)",
    "equity_required": "Equity required (numeric, optional)",
    "interest_rate": "Loan interest rate as decimal (e.g., 0.065 for 6.5%, optional)",
    "ltv": "Loan-to-Value ratio as decimal (e.g., 0.75 for 75%, optional)",
    "ltc": "Loan-to-Cost ratio as decimal (optional)",
    "dscr_at_stabilization": "Debt Service Coverage Ratio at stabilization (numeric, optional)",
    "levered_irr": "Levered IRR as decimal (e.g., 0.2511 for 25.11%, optional)",
    "unlevered_irr": "Unlevered IRR as decimal (optional)",
    "equity_multiple": "Equity multiple (e.g., 2.21, optional)",
    "average_cash_on_cash": "Average cash-on-cash return as decimal (optional)",
    "exit_cap_rate": "Exit cap rate as decimal (e.g., 0.05 for 5%, optional)",
    "yield_on_cost": "Yield on cost as decimal (optional)",
    "hold_period_months": "Hold period in months (integer, optional)",
    "details_json": {{
      "entry_cap_rate": "Entry cap rate (optional)",
      "year_1_occupancy": "Year 1 occupancy rate (optional)",
      "stabilized_occupancy": "Stabilized occupancy rate (optional)",
      "additional_metrics": "Any other relevant financial metrics (optional, use an object for complex data)"
    }}
  }}
}}

IMPORTANT INSTRUCTIONS:
1. Return ONLY valid JSON - no additional text, markdown formatting, or explanations
2. For numeric values, use numbers not strings (e.g., 25.11 not "25.11%")
3. For IRR, interest_rate, cap rates, convert percentages to decimals (25.11% → 0.2511, 6.5% → 0.065)
4. If a field is not found in the document, use null
5. Extract ALL principals mentioned in the document (especially from contact pages)
6. Extract ALL sponsors/operators mentioned (array, not single object)
7. If multiple sponsors mentioned (e.g., "XYZ Capital and ABC Partners"), create separate entries for each
8. Mark the first/most prominent sponsor with is_primary: true
9. For single-sponsor deals, create array with one operator with is_primary: true
10. Be thorough - this is a critical data extraction task
11. For deal_name, use the actual property/portfolio name, not generic terms
12. For internal_code, if not explicitly stated, create one based on the deal name (e.g., "SPRINGDALE-001")
13. Use the EXACT field names specified above - do not use synonyms or variations
14. For land_cost, include purchase price, acquisition cost, acquisition price, or site cost
15. For hard_cost, include construction costs, development costs, building costs, renovation costs, renovation budget, CapEx, capital improvements, or improvement costs
16. For soft_cost, include fees, permits, architecture, engineering costs, closing costs, or transaction costs
17. For total_project_cost, calculate the sum of land_cost + hard_cost + soft_cost if not explicitly stated
18. SECTION PRIORITIZATION - Financial metrics are CRITICAL and commonly found in:
   - Cover page / Executive Summary
   - "Investment Highlights" or "Investment Summary" sections
   - "Capitalization & Projected Returns" tables
   - "Financial Summary" or "Returns" sections
   - "Underwriting Assumptions" pages (often middle or end of deck)
   Search ALL these sections thoroughly before concluding a metric is not present.
19. SQUARE FOOTAGE DISAMBIGUATION - For "building_sf", extract TOTAL PROPERTY square footage:
   - Look for: "Total SF", "Building Size", "Gross Building Area", "Rentable SF", "Total Square Feet", "Area"
   - DO NOT use: "Average Unit Size", "Unit SF", "Typical Unit", individual unit square footages
   - Example: If document says "718 SF average unit" and "14,360 SF total building", use 14,360
20. FINANCIAL METRIC VARIATIONS - Map these common variations to standard fields:
   - levered_irr: "Levered IRR", "LP IRR", "Projected LP IRR, Net", "Net IRR", "IRR to Equity"
   - unlevered_irr: "Unlevered IRR", "Gross IRR", "Projected IRR, Gross", "Project Level IRR"
   - equity_multiple: "Equity Multiple", "EM", "MOIC", "Projected EM", "Projected LP EM, Net", "Net EM"
   - entry_cap_rate: "Entry Cap Rate", "Going-In Cap Rate", "Purchase Cap Rate"
   - exit_cap_rate: "Exit Cap Rate", "Terminal Cap Rate", "Reversion Cap Rate"
   - yield_on_cost: "Yield on Cost", "YoC", "Stabilized YoC", "Stabilized Yield"
   - dscr_at_stabilization: "DSCR", "Debt Service Coverage Ratio", "Stabilized DSCR"
   Convert ALL percentages to decimals (25.6% → 0.256, 2.4x → 2.4)
21. METRIC EXTRACTION PRIORITY - These are HIGH PRIORITY, extract if present:
   - levered_irr (Levered/LP/Net IRR)
   - equity_multiple (Equity Multiple/EM/MOIC)
   - dscr_at_stabilization (DSCR)
   - total_project_cost or land_cost (Acquisition/Purchase Price)
   - equity_required (Equity/LP Equity)
22. PRIMARY DEAL FOCUS - CRITICAL: Extract data for the PRIMARY investment opportunity being offered:
   - IGNORE sections titled: "Track Record", "Case Studies", "Past Performance", "Realized Deals", "Portfolio History", "Success Stories", "Prior Investments"
   - The PRIMARY deal is usually featured prominently on the cover page and has detailed financial projections
   - Case studies are HISTORICAL deals already completed - do NOT extract these
   - If multiple properties are mentioned, extract the one being OFFERED FOR INVESTMENT (usually the first/main property)
   - Look for phrases like "Investment Opportunity", "Offering", "Current Deal", "Target Property"
   - The primary deal typically has forward-looking projections (hold period, exit strategy)
   - Case studies typically show historical returns and sale dates in the past

Return only the JSON object, nothing else."""

    return prompt


def _parse_extraction_response(response_text: str) -> Dict[str, Any]:
    """
    Parse the JSON response from Claude.

    Handles cases where Claude might wrap JSON in markdown code blocks.
    """
    try:
        # Remove markdown code blocks if present
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Parse JSON
        data = json.loads(text)

        # Validate required fields
        if "deal" not in data or "deal_name" not in data["deal"]:
            raise LLMExtractionError("Missing required field: deal.deal_name")

        # Handle backward compatibility: singular operator → operators array
        if "operator" in data and "operators" not in data:
            data["operators"] = [data["operator"]] if data["operator"] else []
            del data["operator"]
        elif "operators" not in data:
            data["operators"] = []

        # Ensure at least one primary if multiple sponsors
        if len(data["operators"]) > 1:
            has_primary = any(op.get("is_primary", False) for op in data["operators"])
            if not has_primary:
                data["operators"][0]["is_primary"] = True
        elif len(data["operators"]) == 1:
            data["operators"][0]["is_primary"] = True

        # Normalize underwriting fields to handle any variations
        if "underwriting" in data:
            data["underwriting"] = _normalize_underwriting_fields(data["underwriting"])

        # Validate extracted values (logs warnings, doesn't fail)
        _validate_extracted_values(data)

        return data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {str(e)}")
        logger.error(f"Response text: {response_text[:500]}")
        raise LLMExtractionError(f"Invalid JSON response from Claude: {str(e)}")

def _normalize_underwriting_fields(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize underwriting field names to handle variations and aliases.

    This provides a fallback in case the LLM uses alternative field names.
    """
    normalized = {}

    # Define field aliases (target_field: [list of possible aliases])
    field_aliases = {
        "land_cost": ["purchase_price", "site_cost", "acquisition_cost", "land_acquisition_cost", "land_purchase"],
        "hard_cost": ["construction_cost", "development_cost", "building_cost", "hard_costs"],
        "soft_cost": ["soft_costs", "fees", "permit_costs"],
        "total_project_cost": ["total_cost", "total_development_cost", "project_cost"],
        "loan_amount": ["debt", "loan", "debt_amount"],
        "equity_required": ["equity", "equity_investment", "required_equity"],
        "interest_rate": ["loan_rate", "debt_rate", "rate"],
        "ltv": ["loan_to_value", "loan_to_value_ratio"],
        "ltc": ["loan_to_cost", "loan_to_cost_ratio"],
        "levered_irr": ["leveraged_irr", "irr_levered"],
        "unlevered_irr": ["unleveraged_irr", "irr_unlevered"],
        "equity_multiple": ["multiple", "moic", "equity_mult"],
        "average_cash_on_cash": ["cash_on_cash", "coc", "avg_coc"],
        "exit_cap_rate": ["exit_cap", "terminal_cap_rate", "terminal_cap"],
        "yield_on_cost": ["yoc", "yield"],
        "hold_period_months": ["hold_period", "investment_period_months"],
    }

    # First, copy all fields that already use standard names
    for key, value in raw_data.items():
        normalized[key] = value

    # Then, check for aliases and map them to standard names
    for standard_field, aliases in field_aliases.items():
        # If standard field doesn't exist, check aliases
        if standard_field not in normalized or normalized[standard_field] is None:
            for alias in aliases:
                if alias in raw_data and raw_data[alias] is not None:
                    normalized[standard_field] = raw_data[alias]
                    logger.info(f"Normalized field: {alias} → {standard_field}")
                    break

    return normalized


def merge_extraction_data(pdf_data: Dict[str, Any], excel_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge PDF narrative with Excel financials.
    Excel takes precedence for all financial metrics.

    Args:
        pdf_data: Extracted data from PDF (deal narrative, sponsors, etc.)
        excel_data: Extracted data from Excel (financial metrics)

    Returns:
        Merged dictionary with PDF narrative + Excel financials
    """
    merged = pdf_data.copy()

    # Override all underwriting fields with Excel data
    if "underwriting" in excel_data:
        merged["underwriting"] = excel_data["underwriting"]
        logger.info(f"Merged {len(excel_data['underwriting'])} financial metrics from Excel")

    # Keep deal narrative from PDF (but can enhance with Excel data)
    # Keep operators from PDF (sponsor identification)
    # Keep principals from PDF (team bios)

    # Merge extraction metadata
    pdf_metadata = pdf_data.get("_extraction_metadata", {})
    excel_metadata = excel_data.get("_extraction_metadata", {})

    merged["_extraction_metadata"] = {
        "method": "merged",
        "pdf_source": pdf_metadata,
        "excel_source": excel_metadata,
        "merged": True
    }

    logger.info("Successfully merged PDF and Excel extraction data")

    return merged


def _validate_extracted_values(data: Dict[str, Any]) -> None:
    """
    Validate extracted values for common errors and log warnings.
    Does not raise exceptions - just logs for manual review.
    """
    warnings = []

    # Validate deal fields
    deal = data.get("deal", {})

    # Building SF sanity check
    building_sf = deal.get("building_sf")
    if building_sf is not None:
        if building_sf < 500:
            warnings.append(f"building_sf ({building_sf}) seems very small - may be unit-level, not property-level")
        elif building_sf > 10000000:
            warnings.append(f"building_sf ({building_sf}) seems unrealistically large")

    # Underwriting validations
    underwriting = data.get("underwriting", {})

    # IRR sanity check
    levered_irr = underwriting.get("levered_irr")
    if levered_irr is not None:
        if levered_irr > 1.0:  # 100%
            warnings.append(f"levered_irr ({levered_irr}) exceeds 100% - may be formatted as percentage not decimal")
        elif levered_irr < -0.5:  # -50%
            warnings.append(f"levered_irr ({levered_irr}) is extremely negative")

    # Equity multiple sanity check
    equity_multiple = underwriting.get("equity_multiple")
    if equity_multiple is not None:
        if equity_multiple < 0.5 or equity_multiple > 10:
            warnings.append(f"equity_multiple ({equity_multiple}) outside typical range (0.5-10x)")

    # DSCR sanity check
    dscr = underwriting.get("dscr_at_stabilization")
    if dscr is not None:
        if dscr < 0.5 or dscr > 5:
            warnings.append(f"dscr_at_stabilization ({dscr}) outside typical range (0.5-5.0)")

    # Log all warnings
    if warnings:
        logger.warning(f"Extraction validation warnings ({len(warnings)} issues found):")
        for warning in warnings:
            logger.warning(f"  - {warning}")
