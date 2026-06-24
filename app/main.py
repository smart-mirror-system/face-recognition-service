from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Request, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging

from app.config import settings
from app.core.database import qdrant_db
from app.core.rate_limiter import limiter, validate_image_size
from app.core.auth import get_current_user_id, create_token
from app.core.embedder import FaceDetectionError
from app.services.registration import registration_service
from app.services.recognition import recognition_service
from app.services.deletion import deletion_service


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)-25s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

if settings.ENVIRONMENT == "development":
    logger.info("Running in DEVELOPMENT mode, CORS open")
    allowed_origins = ["*"]
else:
    logger.info("Running in PRODUCTION mode, CORS restricted to %s", settings.FRONTEND_URL)
    allowed_origins = [settings.FRONTEND_URL]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    try:
        qdrant_db.init_qdrant()
    except Exception as e:
        logger.critical("Database initialization failed: %s", e)
        raise
    yield
    logger.info("Shutting down...")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan, debug=settings.DEBUG)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- HTTP ENDPOINTS ---

@app.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.REGISTRATION_RATE_LIMIT)
async def register_face(
    request: Request,
    file: UploadFile = File(...),
    content_length: int = Header(None),
    user_id: str = Depends(get_current_user_id)
):
    if content_length:
        validate_image_size(content_length)

    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image type. Only JPEG and PNG are allowed."
        )

    try:
        image_bytes = await file.read()
        validate_image_size(len(image_bytes))

        point_id = registration_service.register_face_pose(
            user_id=user_id,
            image_bytes=image_bytes
        )

        logger.info("Registered face point=%s user=%s", point_id, user_id)
        return {
            "success": True,
            "message": "Face vector successfully registered.",
            "point_id": point_id,
            "user_id": user_id
        }

    except FaceDetectionError as fde:
        logger.warning("Registration failed for user=%s: %s", user_id, fde)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(fde)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected registration error for user=%s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal processing error."
        )


@app.post("/login", status_code=status.HTTP_200_OK)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def face_login(
    request: Request,
    file: UploadFile = File(...),
    content_length: int = Header(None)
):
    if content_length:
        validate_image_size(content_length)

    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image type. Only JPEG and PNG are allowed."
        )

    try:
        image_bytes = await file.read()
        validate_image_size(len(image_bytes))

        match_result = recognition_service.recognize_face(image_bytes)

        if not match_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Face login failed. Identity unverified."
            )

        uid = match_result["user_id"]
        token = create_token(uid)
        logger.info("Login succeeded user=%s confidence=%.4f", uid, match_result["confidence"])
        return {
            "ok": True,
            "token": token,
            "userId": uid
        }

    except FaceDetectionError as fde:
        logger.warning("Login validation failed: %s", fde)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(fde)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected login error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


# --- FACE DELETION ---

@app.delete("/faces/{point_id}", status_code=status.HTTP_200_OK)
@limiter.limit(settings.DELETE_POINT_RATE_LIMIT)
async def delete_face_point(
    request: Request,
    point_id: str,
    user_id: str = Depends(get_current_user_id)
):
    owner_id = deletion_service.get_point_owner(point_id)
    if owner_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Face vector not found."
        )
    if owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this face vector."
        )

    try:
        deletion_service.delete_point(point_id)
        logger.info("Deleted face point=%s user=%s", point_id, user_id)
        return {
            "success": True,
            "message": "Face vector successfully deleted.",
            "point_id": point_id
        }
    except Exception as e:
        logger.error("Failed to delete point=%s: %s", point_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete face vector."
        )


@app.delete("/faces/user/{target_user_id}", status_code=status.HTTP_200_OK)
@limiter.limit(settings.DELETE_USER_FACES_RATE_LIMIT)
async def delete_user_faces(
    request: Request,
    target_user_id: str,
    user_id: str = Depends(get_current_user_id)
):
    if target_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own face data."
        )

    try:
        deleted_count = deletion_service.delete_user_faces(user_id)
        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No face vectors found for this user."
            )
        logger.info("Deleted %d face vectors for user=%s", deleted_count, user_id)
        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} face vector(s).",
            "deleted_count": deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete faces for user=%s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete face vectors."
        )


# --- HEALTH & READINESS ---

@app.get("/health", status_code=status.HTTP_200_OK)
async def liveness_probe():
    return {"status": "alive"}


@app.get("/ready")
async def readiness_probe():
    errors = {}

    try:
        client = qdrant_db.get_client()
        client.get_collections()
    except Exception as e:
        logger.error("Readiness check failed for Qdrant: %s", e)
        errors["qdrant"] = "Unreachable or initializing"

    try:
        from redis import Redis
        r = Redis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        if not r.ping():
            errors["redis"] = "Ping failed"
    except Exception as e:
        logger.error("Readiness check failed for Redis: %s", e)
        errors["redis"] = "Unreachable"

    if errors:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unready", "dependencies": errors}
        )

    return {"status": "ready", "qdrant": "connected", "redis": "connected"}