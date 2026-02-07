"""
Email Parser Service

Parses inbound emails from webhook providers (SendGrid, Mailgun, etc.)
and extracts structured data for storage as DealDocuments.
"""

import logging
import re
import base64
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)


class EmailParserError(Exception):
    """Raised when email parsing fails"""
    pass


@dataclass
class EmailAttachment:
    """Represents an email attachment"""
    filename: str
    content_type: str
    content: bytes  # Raw file content
    size: int


@dataclass
class ParsedEmail:
    """Structured email data extracted from webhook payload"""
    from_address: str
    from_name: Optional[str]
    to_addresses: list[str]
    cc_addresses: list[str]
    subject: str
    body_text: str
    body_html: Optional[str]
    date: Optional[datetime]
    message_id: Optional[str]
    in_reply_to: Optional[str]
    attachments: list[EmailAttachment]
    raw_headers: dict


def extract_deal_code_from_address(email_address: str) -> Optional[str]:
    """
    Extract deal code from email address using +tag convention.

    Examples:
        deals+ABC123@builder-os.com -> ABC123
        deals+property-oak-grove@domain.com -> property-oak-grove
        inbox@builder-os.com -> None

    Args:
        email_address: The email address to parse

    Returns:
        Deal code if found, None otherwise
    """
    # Match pattern: anything+{code}@domain
    match = re.search(r'\+([^@]+)@', email_address)
    if match:
        return match.group(1)
    return None


def extract_deal_code_from_subject(subject: str) -> Optional[str]:
    """
    Extract deal code from email subject line.

    Looks for patterns like:
        [ABC123] Subject here
        Re: [ABC123] Subject here
        Deal ABC123 - Update

    Args:
        subject: Email subject line

    Returns:
        Deal code if found, None otherwise
    """
    # Pattern 1: [CODE] at start (with optional Re:/Fwd:)
    match = re.search(r'(?:Re:|Fwd:|FW:)?\s*\[([A-Za-z0-9-_]+)\]', subject, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 2: "Deal CODE" or "Deal: CODE"
    match = re.search(r'Deal[:\s]+([A-Za-z0-9-_]+)', subject, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def parse_sendgrid_webhook(payload: dict) -> ParsedEmail:
    """
    Parse email from SendGrid Inbound Parse webhook.

    SendGrid sends multipart/form-data with fields:
    - from: sender email
    - to: recipient(s)
    - subject: email subject
    - text: plain text body
    - html: HTML body (optional)
    - attachments: number of attachments
    - attachment1, attachment2, etc: actual files
    - headers: raw email headers as text

    Args:
        payload: Dictionary of form fields from webhook

    Returns:
        ParsedEmail object with structured data

    Raises:
        EmailParserError: If required fields are missing
    """
    try:
        # Required fields
        from_field = payload.get('from', '')
        to_field = payload.get('to', '')
        subject = payload.get('subject', '(No Subject)')

        if not from_field:
            raise EmailParserError("Missing 'from' field in email")

        # Parse from address and name
        from_match = re.match(r'(?:"?([^"<]*)"?\s*)?<?([^>]+)>?', from_field)
        if from_match:
            from_name = from_match.group(1).strip() if from_match.group(1) else None
            from_address = from_match.group(2).strip()
        else:
            from_name = None
            from_address = from_field

        # Parse to addresses
        to_addresses = [addr.strip() for addr in to_field.split(',') if addr.strip()]

        # Parse CC addresses
        cc_field = payload.get('cc', '')
        cc_addresses = [addr.strip() for addr in cc_field.split(',') if addr.strip()]

        # Get body content
        body_text = payload.get('text', '')
        body_html = payload.get('html')

        # Parse date from headers if available
        date = None
        headers_text = payload.get('headers', '')
        if headers_text:
            date_match = re.search(r'^Date:\s*(.+)$', headers_text, re.MULTILINE | re.IGNORECASE)
            if date_match:
                try:
                    date = parsedate_to_datetime(date_match.group(1))
                except Exception:
                    pass

        # If no date from headers, use current time
        if not date:
            date = datetime.utcnow()

        # Extract message ID
        message_id = None
        if headers_text:
            msg_id_match = re.search(r'^Message-ID:\s*<?([^>\s]+)>?', headers_text, re.MULTILINE | re.IGNORECASE)
            if msg_id_match:
                message_id = msg_id_match.group(1)

        # Extract In-Reply-To
        in_reply_to = None
        if headers_text:
            reply_match = re.search(r'^In-Reply-To:\s*<?([^>\s]+)>?', headers_text, re.MULTILINE | re.IGNORECASE)
            if reply_match:
                in_reply_to = reply_match.group(1)

        # Parse raw headers into dict
        raw_headers = {}
        if headers_text:
            for line in headers_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    raw_headers[key.strip()] = value.strip()

        # Handle attachments
        attachments = []
        num_attachments = int(payload.get('attachments', 0))

        for i in range(1, num_attachments + 1):
            attachment_info = payload.get(f'attachment-info')
            attachment_file = payload.get(f'attachment{i}')

            if attachment_file:
                # attachment_file is typically a file-like object or bytes
                if hasattr(attachment_file, 'read'):
                    content = attachment_file.read()
                    filename = getattr(attachment_file, 'filename', f'attachment{i}')
                    content_type = getattr(attachment_file, 'content_type', 'application/octet-stream')
                elif isinstance(attachment_file, bytes):
                    content = attachment_file
                    filename = f'attachment{i}'
                    content_type = 'application/octet-stream'
                else:
                    continue

                attachments.append(EmailAttachment(
                    filename=filename,
                    content_type=content_type,
                    content=content,
                    size=len(content)
                ))

        logger.info(f"Parsed SendGrid email: from={from_address}, subject={subject}, attachments={len(attachments)}")

        return ParsedEmail(
            from_address=from_address,
            from_name=from_name,
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            date=date,
            message_id=message_id,
            in_reply_to=in_reply_to,
            attachments=attachments,
            raw_headers=raw_headers
        )

    except EmailParserError:
        raise
    except Exception as e:
        raise EmailParserError(f"Failed to parse SendGrid webhook: {str(e)}")


def parse_mailgun_webhook(payload: dict) -> ParsedEmail:
    """
    Parse email from Mailgun Routes webhook.

    Mailgun sends similar structure to SendGrid with some differences:
    - sender: sender email
    - recipient: recipient email
    - from: full from header
    - subject: email subject
    - body-plain: plain text body
    - body-html: HTML body
    - attachment-count: number of attachments
    - attachment-x: attachment files

    Args:
        payload: Dictionary of form fields from webhook

    Returns:
        ParsedEmail object with structured data
    """
    try:
        # Map Mailgun fields to our expected format
        mapped_payload = {
            'from': payload.get('from', payload.get('sender', '')),
            'to': payload.get('recipient', ''),
            'cc': payload.get('Cc', ''),
            'subject': payload.get('subject', '(No Subject)'),
            'text': payload.get('body-plain', ''),
            'html': payload.get('body-html'),
            'headers': payload.get('message-headers', ''),
            'attachments': payload.get('attachment-count', 0),
        }

        # Copy attachment fields
        for key, value in payload.items():
            if key.startswith('attachment'):
                mapped_payload[key] = value

        # Use SendGrid parser with mapped payload
        return parse_sendgrid_webhook(mapped_payload)

    except EmailParserError:
        raise
    except Exception as e:
        raise EmailParserError(f"Failed to parse Mailgun webhook: {str(e)}")


def format_email_as_text(parsed_email: ParsedEmail) -> str:
    """
    Format parsed email as readable text for storage/display.

    Args:
        parsed_email: ParsedEmail object

    Returns:
        Formatted text representation of the email
    """
    lines = [
        "--- Forwarded Email ---",
        f"From: {parsed_email.from_name or ''} <{parsed_email.from_address}>".strip(),
        f"To: {', '.join(parsed_email.to_addresses)}",
    ]

    if parsed_email.cc_addresses:
        lines.append(f"Cc: {', '.join(parsed_email.cc_addresses)}")

    lines.append(f"Subject: {parsed_email.subject}")

    if parsed_email.date:
        lines.append(f"Date: {parsed_email.date.isoformat()}")

    if parsed_email.attachments:
        attachment_names = [a.filename for a in parsed_email.attachments]
        lines.append(f"Attachments: {', '.join(attachment_names)}")

    lines.append("")
    lines.append("--- Body ---")
    lines.append(parsed_email.body_text or "(No text content)")

    return "\n".join(lines)


def get_email_metadata(parsed_email: ParsedEmail) -> dict:
    """
    Extract metadata dict for storage in DealDocument.metadata_json.

    Args:
        parsed_email: ParsedEmail object

    Returns:
        Dictionary of email metadata
    """
    return {
        "email": {
            "from_address": parsed_email.from_address,
            "from_name": parsed_email.from_name,
            "to_addresses": parsed_email.to_addresses,
            "cc_addresses": parsed_email.cc_addresses,
            "subject": parsed_email.subject,
            "date": parsed_email.date.isoformat() if parsed_email.date else None,
            "message_id": parsed_email.message_id,
            "in_reply_to": parsed_email.in_reply_to,
            "has_attachments": len(parsed_email.attachments) > 0,
            "attachment_count": len(parsed_email.attachments),
            "attachment_names": [a.filename for a in parsed_email.attachments],
        }
    }
