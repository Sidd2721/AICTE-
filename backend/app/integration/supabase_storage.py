import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_supabase_configured() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)


def _get_headers() -> dict[str, str]:
    key = settings.SUPABASE_SERVICE_ROLE_KEY or ""
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }


def ensure_bucket_exists(bucket_name: str | None = None) -> bool:
    if not is_supabase_configured():
        return False
    bucket = bucket_name or settings.SUPABASE_STORAGE_BUCKET or "fdr-vault"
    base_url = str(settings.SUPABASE_URL).rstrip("/")
    url = f"{base_url}/storage/v1/bucket"
    headers = _get_headers()
    headers["Content-Type"] = "application/json"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                url,
                headers=headers,
                json={"id": bucket, "name": bucket, "public": False},
            )
            if resp.status_code in (200, 201) or "already exists" in resp.text.lower():
                return True
            logger.warning(
                "Bucket creation returned %s: %s", resp.status_code, resp.text
            )
            return resp.status_code < 400
    except Exception as exc:
        logger.warning("Failed to verify/create Supabase storage bucket: %s", exc)
        return False


def upload_to_supabase_vault(
    storage_key: str, data: bytes, content_type: str = "application/octet-stream"
) -> str:
    if not is_supabase_configured():
        raise RuntimeError("Supabase credentials not configured")
    bucket = settings.SUPABASE_STORAGE_BUCKET or "fdr-vault"
    base_url = str(settings.SUPABASE_URL).rstrip("/")
    url = f"{base_url}/storage/v1/object/{bucket}/{storage_key}"
    headers = _get_headers()
    headers["x-upsert"] = "true"
    headers["Content-Type"] = content_type

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, headers=headers, content=data)
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Supabase Storage upload failed ({resp.status_code}): {resp.text}"
            )
    return f"supabase://{bucket}/{storage_key}"


def download_from_supabase_vault(storage_key: str) -> bytes:
    if not is_supabase_configured():
        raise RuntimeError("Supabase credentials not configured")
    bucket = settings.SUPABASE_STORAGE_BUCKET or "fdr-vault"
    # Strip protocol prefix if present
    clean_key = storage_key.replace(f"supabase://{bucket}/", "")
    base_url = str(settings.SUPABASE_URL).rstrip("/")
    url = f"{base_url}/storage/v1/object/authenticated/{bucket}/{clean_key}"
    headers = _get_headers()

    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
        if resp.status_code >= 400:
            raise FileNotFoundError(
                f"Supabase Storage object {storage_key} not found ({resp.status_code})"
            )
        return resp.content
