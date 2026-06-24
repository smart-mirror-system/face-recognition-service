import logging
from app.core.embedder import embedder
from app.core.database import qdrant_db
from app.config import settings

logger = logging.getLogger(__name__)

class RecognitionService:
    def __init__(self):
        self.db_client = qdrant_db.get_client()
        self.collection_name = settings.COLLECTION_NAME
        self.similarity_threshold = settings.SIMILARITY_THRESHOLD

    def recognize_face(self, image_bytes: bytes) -> dict | None:
        query_vector = embedder.extract_vector(image_bytes)

        results = self.db_client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=1,
            with_payload=True
        ).points

        if not results:
            logger.info("No registered faces in the database")
            return None

        match = results[0]
        matched_user_id = match.payload.get("user_id")
        confidence = match.score

        logger.info("Login attempt user=%s confidence=%.4f threshold=%.2f",
                    matched_user_id, confidence, self.similarity_threshold)

        if confidence < self.similarity_threshold:
            logger.info("Login rejected user=%s confidence=%.4f below threshold %.2f",
                        matched_user_id, confidence, self.similarity_threshold)
            return None

        return {
            "user_id": str(matched_user_id),
            "confidence": confidence
        }

recognition_service = RecognitionService()