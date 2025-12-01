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


def _build_extraction_prompt(pdf_text: str) -> str:
    """
    Build the extraction prompt for Claude.

    Uses a comprehensive prompt that extracts all data in one pass.
    """
    # Truncate text if too long (keep first ~50k chars to stay within context limits)
    if len(pdf_text) > 50000:
        pdf_text = pdf_text[:50000] + "\n\n[... text truncated ...]"

    prompt = f"""You are analyzing a commercial real estate investment memorandum. Extract all relevant structured data from this document.

DOCUMENT TEXT:
{pdf_text}

---

Please extract the following information and return it as valid JSON:

{{
  "operator": {{
    "name": "Company/operator name (required)",
    "legal_name": "Legal entity name if different (optional)",
    "website_url": "Website URL (optional)",
    "hq_city": "Headquarters city (optional)",
    "hq_state": "Headquarters state (optional)",
    "hq_country": "Headquarters country (optional)",
    "primary_geography_focus": "Primary geographic focus area (optional)",
    "primary_asset_type_focus": "Primary asset type focus (optional)",
    "description": "Brief description of the operator (optional)"
  }},
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
    "purchase_price": "Purchase price (numeric, optional)",
    "renovation_budget": "Renovation/CapEx budget (numeric, optional)",
    "total_project_cost": "Total project cost (numeric, optional)",
    "loan_amount": "Loan amount (numeric, optional)",
    "equity_required": "Equity required (numeric, optional)",
    "levered_irr": "Levered IRR as decimal (e.g., 0.2511 for 25.11%, optional)",
    "unlevered_irr": "Unlevered IRR as decimal (optional)",
    "equity_multiple": "Equity multiple (e.g., 2.21, optional)",
    "average_cash_on_cash": "Average cash-on-cash return as decimal (optional)",
    "hold_period_months": "Hold period in months (integer, optional)",
    "details_json": {{
      "exit_cap_rate": "Exit cap rate (optional)",
      "entry_cap_rate": "Entry cap rate (optional)",
      "year_1_occupancy": "Year 1 occupancy rate (optional)",
      "stabilized_occupancy": "Stabilized occupancy rate (optional)",
      "additional_metrics": "Any other relevant financial metrics (optional)"
    }}
  }}
}}

IMPORTANT INSTRUCTIONS:
1. Return ONLY valid JSON - no additional text, markdown formatting, or explanations
2. For numeric values, use numbers not strings (e.g., 25.11 not "25.11%")
3. For IRR values, convert percentages to decimals (25.11% → 0.2511)
4. If a field is not found in the document, use null
5. Extract ALL principals mentioned in the document (especially from contact pages)
6. Be thorough - this is a critical data extraction task
7. For deal_name, use the actual property/portfolio name, not generic terms
8. For internal_code, if not explicitly stated, create one based on the deal name (e.g., "SPRINGDALE-001")

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
        if "operator" not in data or "name" not in data["operator"]:
            raise LLMExtractionError("Missing required field: operator.name")
        if "deal" not in data or "deal_name" not in data["deal"]:
            raise LLMExtractionError("Missing required field: deal.deal_name")

        return data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {str(e)}")
        logger.error(f"Response text: {response_text[:500]}")
        raise LLMExtractionError(f"Invalid JSON response from Claude: {str(e)}")
