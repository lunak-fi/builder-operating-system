"""
One-time script to upload existing local files to Supabase Storage.

Queries documents where storage_path IS NULL and file_url points to a
local file that still exists on disk.

Usage:
    python -m scripts.backfill_storage
"""

import logging
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from app.db.database import SessionLocal
from app.models import DealDocument, PendingEmailAttachment
from app.services.storage import upload_file, get_storage_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backfill_deal_documents():
    """Upload existing deal documents to Supabase Storage."""
    db = SessionLocal()
    try:
        docs = db.query(DealDocument).filter(
            DealDocument.storage_path.is_(None),
            DealDocument.file_url != "",
        ).all()

        logger.info(f"Found {len(docs)} documents without storage_path")

        uploaded = 0
        for doc in docs:
            local_path = doc.file_url
            if not Path(local_path).exists():
                logger.warning(f"  Skipping {doc.id} — local file missing: {local_path}")
                continue

            deal_folder = f"deals/{doc.deal_id}" if doc.deal_id else "unlinked"
            storage_dest = f"{deal_folder}/documents/{doc.file_name}"

            result = upload_file(local_path, storage_dest)
            if result:
                doc.storage_path = result
                uploaded += 1
                logger.info(f"  Uploaded {doc.id}: {storage_dest}")
            else:
                logger.error(f"  Failed to upload {doc.id}")

        db.commit()
        logger.info(f"Backfill complete: {uploaded}/{len(docs)} documents uploaded")
    finally:
        db.close()


def backfill_pending_attachments():
    """Upload existing pending email attachments to Supabase Storage."""
    db = SessionLocal()
    try:
        attachments = db.query(PendingEmailAttachment).filter(
            PendingEmailAttachment.storage_path.is_(None),
        ).all()

        logger.info(f"Found {len(attachments)} pending attachments without storage_path")

        uploaded = 0
        for att in attachments:
            local_path = att.storage_url
            if not Path(local_path).exists():
                logger.warning(f"  Skipping {att.id} — local file missing: {local_path}")
                continue

            storage_dest = f"pending/{att.pending_email_id}/{att.file_name}"

            result = upload_file(local_path, storage_dest, att.content_type)
            if result:
                att.storage_path = result
                uploaded += 1
                logger.info(f"  Uploaded {att.id}: {storage_dest}")
            else:
                logger.error(f"  Failed to upload {att.id}")

        db.commit()
        logger.info(f"Backfill complete: {uploaded}/{len(attachments)} attachments uploaded")
    finally:
        db.close()


if __name__ == "__main__":
    client = get_storage_client()
    if not client:
        logger.error("Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")
        exit(1)

    backfill_deal_documents()
    backfill_pending_attachments()
    logger.info("Done!")
