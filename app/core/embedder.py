import numpy as np
import cv2
from deepface import DeepFace
import logging

logger = logging.getLogger(__name__)

class FaceDetectionError(Exception):
    pass

class FaceEmbedder:
    def __init__(self):
        self.model_name = "Facenet512"
        self.detector_backend = "mtcnn"

    def extract_vector(self, image_bytes: bytes) -> list[float]:
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                raise ValueError("Could not decode the uploaded image.")

            results = DeepFace.represent(
                img_path=img,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=True,
                align=True
            )

            if len(results) > 0:
                embedding = results[0]["embedding"]
                return embedding
            else:
                raise ValueError("No face detected.")

        except ValueError as ve:
            logger.warning("Face extraction failed: %s", ve)
            raise FaceDetectionError("No clear face detected. Please adjust lighting or position.")

        except Exception as e:
            logger.error("Internal embedder error: %s", e)
            raise

embedder = FaceEmbedder()