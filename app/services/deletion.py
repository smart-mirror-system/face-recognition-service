import logging
from qdrant_client.http import models
from app.core.database import qdrant_db
from app.config import settings

logger = logging.getLogger(__name__)

class DeletionService:
    def __init__(self):
        self.db_client = qdrant_db.get_client()
        self.collection_name = settings.COLLECTION_NAME

    def get_point_owner(self, point_id: str) -> str | None:
        records = self.db_client.retrieve(
            collection_name=self.collection_name,
            ids=[point_id],
            with_payload=True
        )
        if not records:
            return None
        return records[0].payload.get("user_id")

    def delete_point(self, point_id: str) -> bool:
        result = self.db_client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(points=[point_id])
        )
        return result.status.value == "completed"

    def delete_user_faces(self, user_id: str) -> int:
        scroll_results = self.db_client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id)
                    )
                ]
            ),
            limit=10000,
            with_payload=False
        )
        points = scroll_results[0]
        if not points:
            logger.info("No face vectors found for user=%s", user_id)
            return 0

        point_ids = [p.id for p in points]
        self.db_client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(points=point_ids)
        )
        logger.info("Deleted %d face vectors for user=%s", len(point_ids), user_id)
        return len(point_ids)

deletion_service = DeletionService()
