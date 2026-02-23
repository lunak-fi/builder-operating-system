"""
Supabase Storage service for durable file storage.

Uploads deal files (PDFs, Excel models, etc.) to Supabase Storage
so they persist across Railway redeployments.

Returns None silently when Supabase isn't configured — app works without it.
"""

import logging
import os
import mimetypes

logger = logging.getLogger(__name__)

_client = None
_client_initialized = False


def _get_bucket():
    return os.getenv("SUPABASE_STORAGE_BUCKET", "deal-files")


def get_storage_client():
    """Cached Supabase client singleton. Returns None if not configured."""
    global _client, _client_initialized

    if _client_initialized:
        return _client

    _client_initialized = True

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        logger.info("Supabase not configured — file storage disabled")
        return None

    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("Supabase storage client initialized")
        return _client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def upload_file(local_path: str, storage_path: str, content_type: str = None) -> str | None:
    """
    Upload a file to Supabase Storage.

    Args:
        local_path: Path to the local file
        storage_path: Destination path in the bucket (e.g. "deals/{id}/documents/file.pdf")
        content_type: MIME type (auto-detected if not provided)

    Returns:
        The storage_path on success, None if storage not configured or upload fails.
    """
    client = get_storage_client()
    if not client:
        return None

    if not content_type:
        content_type, _ = mimetypes.guess_type(local_path)
        content_type = content_type or "application/octet-stream"

    try:
        with open(local_path, "rb") as f:
            file_data = f.read()

        bucket = _get_bucket()
        client.storage.from_(bucket).upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": content_type},
        )

        logger.info(f"Uploaded {local_path} → {storage_path}")
        return storage_path

    except Exception as e:
        logger.error(f"Supabase upload failed for {storage_path}: {e}")
        return None


def move_file(from_path: str, to_path: str) -> str | None:
    """
    Move a file within Supabase Storage (e.g. from unlinked/ to deals/{id}/).

    Returns the new path on success, None on failure.
    """
    client = get_storage_client()
    if not client:
        return None

    try:
        bucket = _get_bucket()
        client.storage.from_(bucket).move(from_path, to_path)
        logger.info(f"Moved {from_path} → {to_path}")
        return to_path
    except Exception as e:
        logger.error(f"Supabase move failed {from_path} → {to_path}: {e}")
        return None


def download_file(storage_path: str, local_path: str) -> bool:
    """
    Download a file from Supabase Storage to a local path.

    Used for re-extraction and Excel analysis when the local copy is missing.

    Args:
        storage_path: Path in the bucket
        local_path: Where to save the downloaded file

    Returns:
        True on success, False on failure.
    """
    client = get_storage_client()
    if not client:
        return False

    try:
        bucket = _get_bucket()
        response = client.storage.from_(bucket).download(storage_path)

        with open(local_path, "wb") as f:
            f.write(response)

        logger.info(f"Downloaded {storage_path} → {local_path}")
        return True

    except Exception as e:
        logger.error(f"Supabase download failed for {storage_path}: {e}")
        return False
