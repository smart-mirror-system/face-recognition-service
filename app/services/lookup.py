import logging
from qdrant_client.http import models
from app.core.database import qdrant_db
from app.config import settings

logger = logging.getLogger(__name__)


class LookupService:
    def __init__(self):
        self.db_client = qdrant_db.get_client()
        self.collection_name = settings.COLLECTION_NAME

    def count_user_faces(self, user_id: str) -> int:
        count_result = self.db_client.count(
            collection_name=self.collection_name,
            count_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id)
                    )
                ]
            )
        )
        return count_result.count

    def user_has_faces(self, user_id: str) -> bool:
        return self.count_user_faces(user_id) > 0


lookup_service = LookupService()
