import uuid
import logging
from qdrant_client.http import models
from app.core.embedder import embedder
from app.core.database import qdrant_db
from app.config import settings

logger = logging.getLogger(__name__)

class RegistrationService:
    def __init__(self):
        self.db_client = qdrant_db.get_client()
        self.collection_name = settings.COLLECTION_NAME

    def register_face_pose(self, user_id: str, image_bytes: bytes) -> str:
        vector = embedder.extract_vector(image_bytes)
        point_id = str(uuid.uuid4())

        point = models.PointStruct(
            id=point_id,
            vector=vector,
            payload={"user_id": user_id}
        )

        logger.info("Registering face point=%s user=%s", point_id, user_id)
        self.db_client.upsert(
            collection_name=self.collection_name,
            wait=True,
            points=[point]
        )

        return point_id

registration_service = RegistrationService()