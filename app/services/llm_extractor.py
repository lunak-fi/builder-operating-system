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
6. Be thorough - this is a critical data extraction task
7. For deal_name, use the actual property/portfolio name, not generic terms
8. For internal_code, if not explicitly stated, create one based on the deal name (e.g., "SPRINGDALE-001")
9. Use the EXACT field names specified above - do not use synonyms or variations
10. For land_cost, include purchase price, acquisition cost, acquisition price, or site cost
11. For hard_cost, include construction costs, development costs, building costs, renovation costs, renovation budget, CapEx, capital improvements, or improvement costs
12. For soft_cost, include fees, permits, architecture, engineering costs, closing costs, or transaction costs
13. For total_project_cost, calculate the sum of land_cost + hard_cost + soft_cost if not explicitly stated

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

        # Normalize underwriting fields to handle any variations
        if "underwriting" in data:
            data["underwriting"] = _normalize_underwriting_fields(data["underwriting"])

        return data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {str(e)}")
        logger.error(f"Response text: {response_text[:500]}")
        raise LLMExtractionError(f"Invalid JSON response from Claude: {str(e)}")


def extract_fund_data_from_text(pdf_text: str) -> Dict[str, Any]:
    """
    Extract structured fund/strategy data from PDF text using Claude AI.

    Args:
        pdf_text: Raw text extracted from PDF

    Returns:
        Dictionary with extracted structured data:
        {
            "operator": {...},
            "principals": [...],
            "fund": {...}
        }

    Raises:
        LLMExtractionError: If extraction fails
    """
    try:
        settings = LLMSettings()
        client = Anthropic(
            api_key=settings.anthropic_api_key,
            max_retries=2
        )

        extraction_prompt = _build_fund_extraction_prompt(pdf_text)

        logger.info("Sending fund extraction request to Claude API")

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

        response_text = message.content[0].text
        logger.info(f"Received fund extraction response from Claude API ({len(response_text)} chars)")

        extracted_data = _parse_fund_extraction_response(response_text)

        logger.info("Successfully extracted fund data from PDF text")
        return extracted_data

    except Exception as e:
        if isinstance(e, LLMExtractionError):
            raise
        raise LLMExtractionError(f"Unexpected error during fund LLM extraction: {str(e)}")


def _build_fund_extraction_prompt(pdf_text: str) -> str:
    """
    Build the extraction prompt for fund/strategy decks.
    """
    if len(pdf_text) > 50000:
        pdf_text = pdf_text[:50000] + "\n\n[... text truncated ...]"

    prompt = f"""You are analyzing a real estate investment fund or strategy deck. This document describes an investment approach/thesis, NOT a specific property deal. Extract all relevant structured data.

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
  "fund": {{
    "name": "Fund or strategy name (required - e.g., 'SFR Fund I', 'Build-to-Rent Strategy')",
    "strategy": "Investment strategy type: SFR, Multifamily, BTR, Mixed, Industrial, etc. (optional)",
    "target_irr": "Target IRR as decimal (e.g., 0.18 for 18%, optional)",
    "target_equity_multiple": "Target equity multiple (e.g., 2.0, optional)",
    "target_geography": "Target investment geography - comma-separated list (e.g., 'Texas, Florida, Arizona', optional)",
    "target_asset_types": "Target asset types - comma-separated list (e.g., 'SFR, BTR', optional)",
    "fund_size": "Target fund size in dollars (numeric, optional)",
    "gp_commitment": "GP commitment amount in dollars (numeric, optional)",
    "management_fee": "Annual management fee as decimal (e.g., 0.02 for 2%, optional)",
    "carried_interest": "Carried interest/promote as decimal (e.g., 0.20 for 20%, optional)",
    "preferred_return": "Preferred return hurdle as decimal (e.g., 0.08 for 8%, optional)",
    "details_json": {{
      "investment_thesis": "Brief investment thesis (optional)",
      "target_deal_size": "Target deal size range (optional)",
      "target_hold_period": "Target hold period (optional)",
      "track_record": "Summary of track record (optional)",
      "additional_info": "Any other relevant fund information (optional)"
    }}
  }}
}}

IMPORTANT INSTRUCTIONS:
1. Return ONLY valid JSON - no additional text, markdown formatting, or explanations
2. For numeric values, use numbers not strings (e.g., 0.18 not "18%")
3. For IRR, fees, and returns, convert percentages to decimals (18% → 0.18, 2% → 0.02)
4. If a field is not found in the document, use null
5. Extract ALL principals/team members mentioned in the document
6. For fund.name, use the actual fund name or create a descriptive name based on strategy
7. This is a STRATEGY deck - focus on TARGET metrics and investment approach, not specific deal metrics

Return only the JSON object, nothing else."""

    return prompt


def _parse_fund_extraction_response(response_text: str) -> Dict[str, Any]:
    """
    Parse the JSON response from Claude for fund extraction.
    """
    try:
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)

        if "operator" not in data or "name" not in data["operator"]:
            raise LLMExtractionError("Missing required field: operator.name")
        if "fund" not in data or "name" not in data["fund"]:
            raise LLMExtractionError("Missing required field: fund.name")

        return data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse fund JSON response: {str(e)}")
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
