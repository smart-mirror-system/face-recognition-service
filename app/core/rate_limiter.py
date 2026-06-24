from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def get_client_real_ip(request: Request) -> str:
    if settings.BEHIND_GATEWAY:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

    return get_remote_address(request)

limiter = Limiter(key_func=get_client_real_ip)

def validate_image_size(content_length: int):
    if content_length > settings.MAX_IMAGE_SIZE_BYTES:
        max_mb = settings.MAX_IMAGE_SIZE_BYTES / (1024 * 1024)
        logger.warning("Upload rejected: %d bytes exceeds %s limit", content_length, f"{max_mb:.0f}MB")
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {max_mb:.1f}MB."
        )