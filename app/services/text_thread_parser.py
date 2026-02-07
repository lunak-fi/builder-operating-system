import json
import logging
from typing import Dict, Any
from datetime import datetime
from anthropic import Anthropic

from app.services.llm_extractor import LLMSettings

logger = logging.getLogger(__name__)


class ThreadExtractionError(Exception):
    """Raised when text thread extraction fails"""
    pass


def extract_thread_insights(thread_content: str) -> dict:
    """
    Extract structured insights from a text/SMS thread using Claude API.

    Args:
        thread_content: Full text thread content (copy-pasted from SMS/text)

    Returns:
        {
            "participants": ["John", "Sarah", ...],
            "key_topics": ["Deal name", "cap rate assumptions", ...],
            "action_items": [
                {
                    "description": "Respond to sponsor by Friday",
                    "assignee": "John" | null,
                    "priority": "high" | "medium" | "low"
                }
            ],
            "concerns": ["Cap rate assumptions may be aggressive", ...],
            "key_decisions": ["Agreed to proceed with due diligence", ...],
            "sentiment": "positive" | "neutral" | "concerned",
            "summary": "Brief 2-3 sentence summary of the thread",
            "extracted_at": "2026-02-06T14:40:00Z",
            "model": "claude-sonnet-4-20250514"
        }

    Raises:
        ThreadExtractionError: If extraction fails
    """
    try:
        # Initialize Anthropic client
        settings = LLMSettings()
        client = Anthropic(
            api_key=settings.anthropic_api_key,
            max_retries=2
        )

        # Build prompt
        prompt = _build_extraction_prompt(thread_content)

        logger.info("Sending text thread extraction request to Claude API")

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
        logger.info(f"Received thread insights from Claude API ({len(response_text)} chars)")

        # Parse JSON response
        insights = _parse_extraction_response(response_text)

        # Add metadata
        insights["extracted_at"] = datetime.utcnow().isoformat()
        insights["model"] = "claude-sonnet-4-20250514"

        logger.info("Successfully extracted insights from text thread")
        return insights

    except Exception as e:
        if isinstance(e, ThreadExtractionError):
            raise
        raise ThreadExtractionError(f"Unexpected error during thread extraction: {str(e)}")


def _build_extraction_prompt(thread_content: str) -> str:
    """Build Claude prompt for text thread analysis"""

    # Truncate if needed (30k chars limit for threads)
    if len(thread_content) > 30000:
        thread_content = thread_content[:30000] + "\n\n[TRUNCATED]"

    return f"""Analyze this text message/SMS conversation thread and extract structured insights.

Text Thread:
{thread_content}

Extract the following in JSON format:
{{
    "participants": ["List of names/identifiers of people in the conversation"],
    "key_topics": ["Main topics or subjects discussed"],
    "action_items": [
        {{
            "description": "What needs to be done",
            "assignee": "Person responsible (if clear from context, otherwise null)",
            "priority": "high|medium|low"
        }}
    ],
    "concerns": ["List of concerns, risks, or red flags mentioned"],
    "key_decisions": ["List of decisions made or commitments given"],
    "sentiment": "positive|neutral|concerned",
    "summary": "Brief 2-3 sentence summary of the conversation and its implications"
}}

Focus on:
- Identifying all participants in the conversation
- Extracting concrete action items with clear assignees when mentioned
- Noting any deal-related concerns or risks
- Capturing decisions and commitments
- Providing a concise summary of the conversation's purpose and outcome

IMPORTANT:
1. Return ONLY valid JSON - no additional text, markdown formatting, or explanations
2. If no items found for a category, use empty array []
3. For action items without clear assignees, set assignee to null
4. For sentiment, choose one of: "positive", "neutral", or "concerned"
5. The summary should be actionable and highlight next steps if any

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
        required_fields = ["participants", "key_topics", "action_items", "concerns", "key_decisions", "sentiment", "summary"]
        for field in required_fields:
            if field not in data:
                if field == "summary":
                    data["summary"] = ""
                elif field == "sentiment":
                    data["sentiment"] = "neutral"
                else:
                    data[field] = []

        # Validate sentiment value
        valid_sentiments = ["positive", "neutral", "concerned"]
        if data["sentiment"] not in valid_sentiments:
            logger.warning(f"Invalid sentiment value: {data['sentiment']}, defaulting to 'neutral'")
            data["sentiment"] = "neutral"

        # Ensure lists are lists
        for field in ["participants", "key_topics", "concerns", "key_decisions"]:
            if not isinstance(data.get(field), list):
                data[field] = []

        if not isinstance(data.get("action_items"), list):
            data["action_items"] = []

        # Validate action items structure
        for item in data["action_items"]:
            if not isinstance(item, dict):
                continue
            if "description" not in item:
                item["description"] = "Unspecified action"
            if "priority" not in item:
                item["priority"] = "medium"
            if item.get("priority") not in ["high", "medium", "low"]:
                item["priority"] = "medium"

        return data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {str(e)}")
        logger.error(f"Response text: {response_text[:500]}")
        raise ThreadExtractionError(f"Invalid JSON response from Claude: {str(e)}")
