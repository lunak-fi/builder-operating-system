import logging
from typing import Literal
from anthropic import Anthropic
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class LLMSettings(BaseSettings):
    anthropic_api_key: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ClassificationError(Exception):
    """Raised when document classification fails"""
    pass


def classify_document(pdf_text: str) -> Literal["deal", "fund"]:
    """
    Classify a document as either a deal deck or a fund/strategy deck.

    Args:
        pdf_text: Raw text extracted from PDF

    Returns:
        "deal" if document describes a specific property/investment
        "fund" if document describes an investment strategy/fund without specific property

    Raises:
        ClassificationError: If classification fails
    """
    try:
        settings = LLMSettings()
        client = Anthropic(
            api_key=settings.anthropic_api_key,
            max_retries=2
        )

        # Use a shorter text sample for classification
        text_sample = pdf_text[:20000] if len(pdf_text) > 20000 else pdf_text

        prompt = f"""Analyze this real estate investment document and classify it as one of two types:

1. DEAL DECK - A document about a SPECIFIC property or investment opportunity with:
   - A specific property address or location
   - Specific acquisition/purchase price
   - Specific unit count or square footage
   - Specific financial projections for that property

2. FUND/STRATEGY DECK - A document about an investment STRATEGY or FUND without a specific property:
   - Describes investment thesis/approach
   - Shows TARGET returns (not actual deal projections)
   - Discusses deal CRITERIA (what they look for)
   - May mention fund terms (management fee, carried interest, GP/LP structure)
   - May show track record of past deals
   - Does NOT have a specific property being offered

DOCUMENT TEXT:
{text_sample}

---

Based on the document above, respond with ONLY one word: either "deal" or "fund"
Nothing else - just the single word classification."""

        logger.info("Sending classification request to Claude API")

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = message.content[0].text.strip().lower()
        logger.info(f"Classification result: {response_text}")

        if response_text == "deal":
            return "deal"
        elif response_text == "fund":
            return "fund"
        else:
            # Default to deal if unclear
            logger.warning(f"Unexpected classification response: {response_text}, defaulting to 'deal'")
            return "deal"

    except Exception as e:
        logger.error(f"Classification failed: {str(e)}")
        raise ClassificationError(f"Failed to classify document: {str(e)}")
