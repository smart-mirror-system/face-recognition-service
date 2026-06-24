import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
from app.config import settings

logger = logging.getLogger(__name__)

class QdrantDatabase:
    def __init__(self):
        if settings.QDRANT_API_KEY:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
        else:
            self.client = QdrantClient(url=settings.QDRANT_URL)

    def init_qdrant(self):
        try:
            collections = self.client.get_collections().collections
            existing = [c.name for c in collections]

            if settings.COLLECTION_NAME not in existing:
                logger.info("Creating Qdrant collection '%s' (size=%d, distance=COSINE)",
                            settings.COLLECTION_NAME, settings.VECTOR_SIZE)
                self.client.create_collection(
                    collection_name=settings.COLLECTION_NAME,
                    vectors_config=models.VectorParams(
                        size=settings.VECTOR_SIZE,
                        distance=models.Distance.COSINE
                    )
                )
            else:
                logger.info("Qdrant collection '%s' already exists", settings.COLLECTION_NAME)

        except UnexpectedResponse as e:
            logger.error("Qdrant connection failed: %s", e)
            raise
        except Exception as e:
            logger.error("Unexpected error during Qdrant setup: %s", e)
            raise

    def get_client(self) -> QdrantClient:
        return self.client

qdrant_db = QdrantDatabase()