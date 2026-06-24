import re
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
import logging

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer()


def _parse_expiry(value: str) -> timedelta:
    match = re.fullmatch(r"(\d+)([dhms])", value.strip())
    if not match:
        return timedelta(days=7)
    num = int(match.group(1))
    unit = match.group(2)
    mapping = {"d": "days", "h": "hours", "m": "minutes", "s": "seconds"}
    return timedelta(**{mapping[unit]: num})


def create_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "userId": user_id,
        "iat": now,
        "exp": now + _parse_expiry(settings.JWT_EXPIRES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )

        user_id: str = payload.get("userId")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims. Subject identifier is missing."
            )

        return str(user_id)

    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature has expired. Please authenticate again."
        )
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token."
        )