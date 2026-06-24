# Environment Variables Reference

This document documents all environment variables used across the Mrayti Smart Mirror platform. Variables are grouped by service.

---

## Python AI Service (`app/config.py`)

These variables are consumed by the Python/FastAPI face recognition microservice.

| Variable | Default | Description |
|---|---|---|
| `DEBUG` | `False` | Enable debug mode (`true`/`1`/`t` for enabled) |
| `ENVIRONMENT` | `development` | Runtime environment (`development`, `staging`, `production`) |
| `FRONTEND_URL` | `https://mrayti.com` | Allowed CORS origin for the frontend |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant vector database endpoint |
| `QDRANT_API_KEY` | `""` | API key for Qdrant (leave empty if not required) |
| `QDRANT_COLLECTION_NAME` | `mrayti_faces` | Qdrant collection storing face embeddings |
| `SIMILARITY_THRESHOLD` | `0.65` | Minimum cosine similarity score to accept a face match |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis message broker connection string |
| `REDIS_STREAM_NAME` | `mrayti_events` | Redis stream name for event publishing |
| `REDIS_CONSUMER_GROUP` | `ai_service_group` | Redis consumer group name |
| `JWT_SECRET` | `your-super-shared-secret-change-me` | Shared HMAC secret for JWT verification |
| `MAX_IMAGE_SIZE_BYTES` | `5242880` | Maximum uploaded file size in bytes (default 5 MB) |
| `AUTH_RATE_LIMIT` | `5 per minute` | Rate limit for `/login` endpoint (slowapi format) |
| `REGISTRATION_RATE_LIMIT` | `10 per minute` | Rate limit for `/register` endpoint (slowapi format) |
| `BEHIND_GATEWAY` | `True` | Set to `True` behind Nginx/Traefik to respect `X-Forwarded-For` |

---

## Node.js API Service (Docker Compose)

These variables are consumed by the `smart-mirror-api` container. They are loaded from the `.env` file defined in the `env_file` field of `docker-compose.yaml`.

| Variable | Default / Example | Description |
|---|---|---|
| `PORT` | `3000` | Port the Node.js server listens on |
| `MONGO_URI` | `mongodb://smart-mirror-mongo:27017/smart_mirror` | MongoDB connection string. Use `mongodb://localhost:27017/smart_mirror` for local mongodb, `mongodb://container-name:27017/smart_mirror` for docker or any custom connection string, leave it as it is if you are using the given docker-compose.yaml (if it did not work check the mongo container name in docker-compose.yaml) |
| `JWT_SECRET` | *(no default)* | Secret key used to sign and verify JSON Web Tokens |
| `JWT_EXPIRES` | `7d` | JWT expiration duration (e.g., `7d`, `24h`, `60m`) |
| `GEMINI_API_KEY` | *(no default)* | API key for Google Gemini AI integration |

---

## Docker Compose Environment Summary

Below is a reference `.env` file for use with `docker-compose.yaml`:

```env
# ─── Node.js API Service ───
PORT=3000

# Docker: use the MongoDB service name as hostname
# Local:  mongodb://localhost:27017/smart_mirror
MONGO_URI=mongodb://smart-mirror-mongo:27017/smart_mirror

JWT_SECRET=
JWT_EXPIRES=7d
GEMINI_API_KEY=

# ─── Python AI Service (override defaults from app/config.py) ───
DEBUG=False
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
REDIS_URL=redis://redis:6379/0
JWT_SECRET=
SIMILARITY_THRESHOLD=0.65
```

> **Note:** The `JWT_SECRET` must match between the Node.js API and the Python AI service for token verification to work.
