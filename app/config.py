import os
from dotenv import load_dotenv

# Load variables from a .env file if it exists
load_dotenv()

class Settings:
    # Service Settings
    APP_NAME: str = "Mrayti-AI-Service"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    # Environment Settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://mrayti.com") 
    
    # Qdrant Vector Database Settings
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "mrayti_faces")
    
    # FaceNet Vector Configurations
    VECTOR_SIZE: int = 512 
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", 0.65))  # Minimum cosine similarity for recognition
    # Redis Message Broker Settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    STREAM_NAME: str = os.getenv("REDIS_STREAM_NAME", "mrayti_events")
    CONSUMER_GROUP: str = os.getenv("REDIS_CONSUMER_GROUP", "ai_service_group")

    # Security Settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-super-shared-secret-change-me")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES: str = os.getenv("JWT_EXPIRES", "7d")

    # --- Added Configurable Guardrails ---
    
    # Image Validation Limits
    # Default: 5 * 1024 * 1024 = 5,242,880 bytes (5 MB)
    MAX_IMAGE_SIZE_BYTES: int = int(os.getenv("MAX_IMAGE_SIZE_BYTES", 5242880))
    
    # Rate Limiting Configurations
    # Format string parsed by slowapi (e.g., "5 per minute", "100 per day")
    AUTH_RATE_LIMIT: str = os.getenv("AUTH_RATE_LIMIT", "5 per minute")
    REGISTRATION_RATE_LIMIT: str = os.getenv("REGISTRATION_RATE_LIMIT", "10 per minute")
    DELETE_POINT_RATE_LIMIT: str = os.getenv("DELETE_POINT_RATE_LIMIT", "30 per minute")
    DELETE_USER_FACES_RATE_LIMIT: str = os.getenv("DELETE_USER_FACES_RATE_LIMIT", "10 per minute")
    
    # Network / Gateway Topology
    # Set to True if deployed behind an API Gateway (Nginx, Traefik, etc.) 
    # to enforce extraction of X-Forwarded-For instead of the Gateway's local IP.
    BEHIND_GATEWAY: bool = os.getenv("BEHIND_GATEWAY", "True").lower() in ("true", "1", "t")

settings = Settings()