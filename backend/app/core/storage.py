"""
Storage Handler for CivicPilot.
Uploads images and media to Supabase Storage with automatic local-disk fallback.
Source of truth: docs/CONTRACT.md Section 7.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from backend.app.core.config import get_settings


async def upload_image_bytes(
    file_bytes: bytes,
    original_filename: str = "image.jpg",
    content_type: str = "image/jpeg",
) -> str:
    """
    Upload image bytes to Supabase Storage bucket 'civicpilot-uploads',
    falling back to local disk storage in UPLOAD_DIR.
    Returns the public or accessible URL string.
    """
    settings = get_settings()
    ext = os.path.splitext(original_filename)[1] or ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"

    # 1. Attempt Supabase Storage if configured
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
        try:
            from supabase import create_client  # type: ignore
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
            bucket_name = "civicpilot-uploads"

            # Upload bytes to bucket
            client.storage.from_(bucket_name).upload(
                path=unique_name,
                file=file_bytes,
                file_options={"content-type": content_type},
            )
            # Retrieve public URL
            public_url = client.storage.from_(bucket_name).get_public_url(unique_name)
            return public_url
        except Exception as e:
            print(f"[Storage Warning] Supabase storage upload failed: {e}. Falling back to local disk.")

    # 2. Local disk fallback
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / unique_name
    file_path.write_bytes(file_bytes)

    # Return local API URL
    return f"/api/uploads/{unique_name}"
