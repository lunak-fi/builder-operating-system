import json
import logging
from typing import Dict, Any
from datetime import datetime
from anthropic import Anthropic

from app.services.llm_extractor import LLMSettings

logger = logging.getLogger(__name__)


class TranscriptExtractionError(Exception):
    """Raised when transcript extraction fails"""
    pass


def extract_transcript_insights(transcript_text: str, metadata: dict) -> dict:
    """
    Extract structured insights from transcript using Claude API.

    Args:
        transcript_text: Full transcript content
        metadata: Dict with 'topic' and 'conversation_date'

    Returns:
        {
            "key_decisions": ["Decision text...", ...],
            "action_items": [
                {
                    "description": "Request updated rent roll",
                    "assignee": "John Smith",
                    "priority": "high"
                }
            ],
            "risks": ["Risk description...", ...],
            "sentiment": "positive" | "neutral" | "concerned",
            "extracted_at": "2026-01-15T14:40:00Z",
            "model": "claude-sonnet-4-20250514"
        }

    Raises:
        TranscriptExtractionError: If extraction fails
    """
    try:
        # Initialize Anthropic client
        settings = LLMSettings()
        client = Anthropic(
            api_key=settings.anthropic_api_key,
            max_retries=2
        )

        # Build prompt
        prompt = _build_extraction_prompt(transcript_text, metadata)

        logger.info("Sending transcript extraction request to Claude API")

        # Call Claude API
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0,  # Deterministic extraction
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Extract JSON from response
        response_text = message.content[0].text
        logger.info(f"Received transcript insights from Claude API ({len(response_text)} chars)")

        # Parse JSON response
        insights = _parse_extraction_response(response_text)

        # Add metadata
        insights["extracted_at"] = datetime.utcnow().isoformat()
        insights["model"] = "claude-sonnet-4-20250514"

        logger.info("Successfully extracted insights from transcript")
        return insights

    except Exception as e:
        if isinstance(e, TranscriptExtractionError):
            raise
        raise TranscriptExtractionError(f"Unexpected error during transcript extraction: {str(e)}")


def _build_extraction_prompt(transcript_text: str, metadata: dict) -> str:
    """Build Claude prompt for transcript analysis"""

    topic = metadata.get("topic", "Unknown")
    date = metadata.get("conversation_date", "Unknown")

    # Truncate if needed (50k chars limit)
    if len(transcript_text) > 50000:
        transcript_text = transcript_text[:50000] + "\n\n[TRUNCATED]"

    return f"""Analyze this conversation transcript and extract structured insights.

Transcript Topic: {topic}
Date: {date}

Transcript:
{transcript_text}

Extract the following in JSON format:
{{
    "key_decisions": ["List of key decisions made during conversation"],
    "action_items": [
        {{
            "description": "What needs to be done",
            "assignee": "Person mentioned (if clear from context)",
            "priority": "high|medium|low"
        }}
    ],
    "risks": ["List of risks, concerns, or red flags mentioned"],
    "sentiment": "positive|neutral|concerned"
}}

Focus on:
- Concrete decisions and commitments
- Specific action items with clear assignees
- Deal-related risks and concerns
- Overall sentiment/tone of conversation

IMPORTANT:
1. Return ONLY valid JSON - no additional text, markdown formatting, or explanations
2. If no items found for a category, use empty array []
3. For action items without clear assignees, set assignee to null
4. For sentiment, choose one of: "positive", "neutral", or "concerned"
5. Be thorough - extract ALL relevant information from the transcript

Return only the JSON object, nothing else."""


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
        required_fields = ["key_decisions", "action_items", "risks", "sentiment"]
        for field in required_fields:
            if field not in data:
                raise TranscriptExtractionError(f"Missing required field: {field}")

        # Validate sentiment value
        valid_sentiments = ["positive", "neutral", "concerned"]
        if data["sentiment"] not in valid_sentiments:
            logger.warning(f"Invalid sentiment value: {data['sentiment']}, defaulting to 'neutral'")
            data["sentiment"] = "neutral"

        # Ensure lists are lists
        if not isinstance(data["key_decisions"], list):
            data["key_decisions"] = []
        if not isinstance(data["action_items"], list):
            data["action_items"] = []
        if not isinstance(data["risks"], list):
            data["risks"] = []

        # Validate action items structure
        for item in data["action_items"]:
            if not isinstance(item, dict):
                raise TranscriptExtractionError("Action items must be objects")
            if "description" not in item:
                raise TranscriptExtractionError("Action item missing 'description' field")
            if "priority" not in item:
                item["priority"] = "medium"
            if item["priority"] not in ["high", "medium", "low"]:
                item["priority"] = "medium"

        return data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {str(e)}")
        logger.error(f"Response text: {response_text[:500]}")
        raise TranscriptExtractionError(f"Invalid JSON response from Claude: {str(e)}")
