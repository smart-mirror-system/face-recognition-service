# Mrayti AI Biometrics Service

## Quick Access

- [Overview](#overview)
- [How to Run](#how-to-run)
- [Architecture](#architecture)
  - [Directory Structure](#directory-structure)
  - [Layered Design](#layered-design)
- [API Endpoints](#api-endpoints)
  - [POST /register](#post-register--register-face-pose)
  - [POST /login](#post-login--face-login-biometric-auth)
  - [DELETE /faces/{point_id}](#delete-facespoint_id--delete-face-point)
  - [DELETE /faces/user/{user_id}](#delete-facesuseruser_id--delete-all-user-faces)
  - [GET /faces/count](#get-facescount--check-face-registration-status)
  - [GET /health](#get-health--liveness-probe)
  - [GET /ready](#get-ready--readiness-probe)
- [Data Flow](#data-flow)
  - [Face Registration](#face-registration)
  - [Face Login](#face-login-recognition)
- [Core Components](#core-components)
- [Deployment](#deployment)
  - [Docker](#docker)
  - [Docker Compose Topology](#docker-compose-topology)
  - [Gateway Configuration](#gateway-configuration)
- [Configuration](#configuration)
- [Security](#security)
- [Known Gaps & Future Work](#known-gaps--future-work)

---

## Overview

The AI Service is a high-performance Python/FastAPI microservice dedicated to FaceNet512 facial recognition, Qdrant vector storage, and biometric authentication. It is the core biometric engine of the Smart Mirror platform.

| Attribute | Value |
|---|---|
| **Framework** | FastAPI (Python 3.10) |
| **Face Model** | FaceNet512 (512-dim embeddings) |
| **Face Detector** | MTCNN |
| **Vector Database** | Qdrant (COSINE distance) |
| **Message Broker** | Redis Streams |
| **Authentication** | JWT (HS256, shared secret with Node.js API) |
| **Port** | `8000` (internal) |
| **Startup** | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |

---

## How to Run

### Prerequisites
- Docker & Docker Compose (recommended)
- Python 3.12+ (for local development)

### Using Docker Compose (recommended)

```bash
# 1. Clone and enter the project
git clone <repo-url> && cd face-recognition

# 2. Copy environment file and fill in required values
cp .env.example .env
# Edit .env — at minimum set JWT_SECRET and GEMINI_API_KEY

# 3. Start all services
docker compose up -d
```

The AI service will be available at `http://localhost:8000`. See [API_DOCS.md](./docs/API_DOCS.md) for endpoint details.

### Using Docker (single service)

```bash
docker build -t mrayti-ai-service .
docker run -p 8000:8000 --env-file .env mrayti-ai-service
```

### Local Development (without Docker)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv && source .venv/bin/activate   # Linux/macOS
# or
python -m venv .venv && .venv\Scripts\Activate.ps1  # Windows (PowerShell)

# 2. Install dependencies
pip install -r requirements.txt

# 3. Ensure Qdrant and Redis are running (e.g., via Docker)
docker run -d -p 6333:6333 qdrant/qdrant
docker run -d -p 6379:6379 redis:7-alpine

# 4. Copy and configure environment
cp .env.example .env

# 5. Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Architecture

### Directory Structure

```
app/
├── __init__.py
├── main.py              # FastAPI app, endpoints, startup/shutdown
├── config.py            # Settings class (env-driven configuration)
├── core/
│   ├── __init__.py
│   ├── auth.py          # JWT validation (get_current_user_id dependency)
│   ├── embedder.py      # FaceNet512 embedding engine (FaceEmbedder)
│   ├── database.py      # Qdrant client wrapper (QdrantDatabase)
│   └── rate_limiter.py  # Rate limiter + image size validation
├── services/
│   ├── __init__.py
│   ├── registration.py  # Face registration business logic
│   ├── recognition.py   # Face recognition business logic
│   ├── deletion.py      # Face deletion business logic
│   └── lookup.py        # Face lookup / user existence checks
└── workers/
    ├── __init__.py
    └── deletion_worker.py  # Placeholder for Redis stream consumer
```

### Layered Design

```
main.py          -- HTTP layer, validation, error mapping (controllers)
core/            -- Infrastructure: DB client, ML model, auth, rate limiting
services/        -- Business logic: registration, recognition, deletion
workers/         -- (planned) Background event processing
```

All major components (`FaceEmbedder`, `QdrantDatabase`, `RegistrationService`, `RecognitionService`, `DeletionService`) follow the **singleton pattern** — instantiated once at module level and reused. This ensures:
- `QdrantClient` maintains a connection pool.
- The DeepFace/TF model is loaded only once.
- Rate limiter state is shared across requests.

---

## API Endpoints

### `POST /register` — Register Face Pose

Registers a facial embedding for an authenticated user. Called multiple times during onboarding to capture various angles.

- **Rate limit:** `10 per minute` (configurable via `REGISTRATION_RATE_LIMIT`)
- **Auth:** JWT `Bearer` token required (`userId` claim)
- **Content-Type:** `multipart/form-data`
- **Input:** `file` (JPEG/PNG, max 5 MB)

**Success (201):**
```json
{
  "success": true,
  "message": "Face vector successfully registered.",
  "point_id": "b8a9c2... (UUID v4)",
  "user_id": "user_123"
}
```

**Errors:** `400` (invalid type/size), `401` (JWT), `422` (no face detected), `500` (internal).

### `POST /login` — Face Login (Biometric Auth)

Authenticates a user by comparing a live webcam frame against stored face vectors in Qdrant.

- **Rate limit:** `5 per minute` (configurable via `AUTH_RATE_LIMIT`)
- **Auth:** None (public endpoint — designed for the mirror webcam)
- **Content-Type:** `multipart/form-data`
- **Input:** `file` (JPEG/PNG, max 5 MB)

**Success (200):**
Returns a signed JWT (same format as the Node.js API) that can be used for subsequent authenticated requests.

```json
{
  "ok": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "userId": "6a3b1a6a75b4fd165ed0da44"
}
```

The token is signed with the shared `JWT_SECRET` and expires after `JWT_EXPIRES` (default `7d`).

**Errors:** `400` (invalid type/size), `401` (no match above threshold), `422` (no face detected), `500` (internal).

### `DELETE /faces/{point_id}` — Delete Face Point

Removes a single registered face vector by ID. The authenticated user can only delete their own vectors.

- **Rate limit:** `30 per minute`
- **Auth:** JWT `Bearer` token required (`userId` claim)

**Success (200):**
```json
{
  "success": true,
  "message": "Face vector successfully deleted.",
  "point_id": "b8a9c2... (UUID v4)"
}
```

**Errors:** `401` (JWT), `403` (not owned by user), `404` (not found), `500` (internal).

### `DELETE /faces/user/{user_id}` — Delete All User Faces

Removes all registered face vectors belonging to the authenticated user.

- **Rate limit:** `10 per minute`
- **Auth:** JWT `Bearer` token required (`userId` claim)

**Success (200):**
```json
{
  "success": true,
  "message": "Successfully deleted 3 face vector(s).",
  "deleted_count": 3
}
```

**Errors:** `401` (JWT), `403` (cannot delete another user's data), `404` (no face vectors found), `500` (internal).

### `GET /faces/count` — Check Face Registration Status

Returns the number of face vectors registered for the authenticated user. Used by the frontend to determine whether to show a fresh registration or a re-registration flow.

- **Rate limit:** `30 per minute`
- **Auth:** JWT `Bearer` token required (`userId` claim)

**Success (200):**
```json
{
  "user_id": "6a3b1a6a75b4fd165ed0da44",
  "count": 3,
  "exists": true
}
```

**Errors:** `401` (JWT), `500` (internal).

### `GET /health` — Liveness Probe

Indicates the container process is running. If this fails, the orchestrator restarts the container.

```json
{ "status": "alive" }
```

### `GET /ready` — Readiness Probe

Verifies downstream dependencies (Qdrant, Redis) are operational. If this fails, the gateway removes the instance from the traffic pool.

**Success (200):**
```json
{
  "status": "ready",
  "qdrant": "connected",
  "redis": "connected"
}
```

**Failure (503):**
```json
{
  "status": "unready",
  "dependencies": {
    "qdrant": "Unreachable or initializing",
    "redis": "Ping failed"
  }
}
```

---

## Data Flow

### Face Registration

```
Client/Mirror          Gateway               AI Service                Qdrant
    │                      │                      │                       │
    │ POST /register       │                      │                       │
    │ (image + JWT)        │                      │                       │
    │────────────────────> │                      │                       │
    │                      │ POST /register       │                       │
    │                      │─────────────────────>│                       │
    │                      │                      │  1. Validate JWT      │
    │                      │                      │  2. Validate image    │
    │                      │                      │  3. extract_vector()  │
    │                      │                      │     (DeepFace)        │
    │                      │                      │  4. Generate UUID v4  │
    │                      │                      │  5. PointStruct       │
    │                      │                      │  6. upsert(wait=True) │
    │                      │                      │──────────────────────>│
    │                      │  201 Created         │                       │
    │  {point_id, user}    │  {point_id, user}    │                       │
    │<──────────────────── │<─────────────────────│                       │
```

### Face Login (Recognition)

```
Mirror/User            Gateway               AI Service                Qdrant
    │                     │                      │                       │
    │ POST /login         │                      │                       │
    │ (file, no JWT)      │                      │                       │
    │────────────────────>│                      │                       │
    │                     │ POST /login          │                       │
    │                     │─────────────────────>│                       │
    │                     │                      │  1. Validate image    │
    │                     │                      │  2. extract_vector()  │
    │                     │                      │  3. query_points(     │
    │                     │                      │       limit=1,        │
    │                     │                      │       score_threshold │
    │                     │                      │       )               │
    │                     │                      │──────────────────────>│
    │                     │                      │  [nearest + score]    │
    │                     │                      │<──────────────────────│
    │                     │                      │  4. score < threshold │
    │                     │                      │     → None → 401     │
    │                     │                      │  5. else → {user_id,  │
    │                     │                      │            confidence}│
    │                     │  200 / 401           │                       │
    │<────────────────────│<─────────────────────│                       │
```

---

## Core Components

### `FaceEmbedder` (`app/core/embedder.py`)
- Model: `Facenet512` (512-dim embeddings)
- Detector: `mtcnn` (more accurate than OpenCV Haar cascades)
- Alignment: enabled
- Returns a 512-element `list[float]`
- Raises `FaceDetectionError` (mapped to `422` in endpoints) when no face is detected

### `QdrantDatabase` (`app/core/database.py`)
- Creates collection `mrayti_faces` on startup if not exists
- Vector size: `512`, Distance: `COSINE`
- Supports optional API key auth

### `RegistrationService` (`app/services/registration.py`)
- Generates UUID v4 as point ID
- Stores `PointStruct(id, vector, payload={"user_id": ...})`
- Uses `upsert(wait=True)` for synchronous persistence

### `RecognitionService` (`app/services/recognition.py`)
- Calls `query_points()` with `score_threshold` (default `0.65`)
- Returns `{"user_id": ..., "confidence": score}` or `None`

### `DeletionService` (`app/services/deletion.py`)
- `get_point_owner(point_id)` — retrieves a point's `user_id` payload for ownership verification
- `delete_point(point_id)` — deletes a single point by ID
- `delete_user_faces(user_id)` — scrolls all points matching a user via payload filter, deletes them in batch, returns count

### `LookupService` (`app/services/lookup.py`)
- `count_user_faces(user_id)` — uses Qdrant's efficient `count()` API with a payload filter to return the number of registered face vectors for a user, without loading any vectors
- `user_has_faces(user_id)` — convenience wrapper returning `bool`

### JWT Auth (`app/core/auth.py`)
- `get_current_user_id` — FastAPI dependency that extracts and verifies the JWT from the `Authorization` header
- `create_token(user_id)` — signs a new JWT with the shared `JWT_SECRET` and `JWT_EXPIRES` (default `7d`)
- Decodes with `JWT_SECRET` and `HS256`, extracts `userId` claim
- Raises `401` on invalid/expired tokens

### Rate Limiting (`app/core/rate_limiter.py`)
- Uses `slowapi` with separate limits for auth (5/min) and registration (10/min)
- Respects `X-Forwarded-For` when `BEHIND_GATEWAY=True`
- Validates image size against `MAX_IMAGE_SIZE_BYTES` (default 5 MB)

---

## Deployment

### Docker

The service is containerized using `python:3.10-slim`. The Dockerfile:
1. Installs OpenCV system dependencies (`libgl1-mesa-glx`, `libglib2.0-0`)
2. Pre-downloads FaceNet512 weights at build time for faster startup
3. Runs via `uvicorn` on port `8000`

```bash
docker build -t mrayti-ai-service .
docker run -p 8000:8000 --env-file .env mrayti-ai-service
```

### Docker Compose Topology

```
                    smart-mirror-net
           ┌──────────────────────────────────────┐
           │  MongoDB (27017)    Node API (3000)   │
           └──────────────────────────────────────┘

           Qdrant (6333/6334)    Redis (6379)
                  ▲                  ▲
                  │                  │
                  └──────┬───────────┘
                         │
                   AI Service (8000)
```

The AI service, Qdrant, and Redis communicate via host-mapped ports. The Node.js API and MongoDB are isolated on their own Docker network (`smart-mirror-net`).

### Gateway Configuration

Endpoints are designed to be mounted behind a path-stripping gateway:
- `POST /ai/register` → internal `POST /register`
- `POST /ai/login` → internal `POST /login`
- `DELETE /ai/faces/{point_id}` → internal `DELETE /faces/{point_id}`
- `DELETE /ai/faces/user/{user_id}` → internal `DELETE /faces/user/{user_id}`
- `GET /ai/faces/count` → internal `GET /faces/count`
- `GET /ai/health` → internal `GET /health`
- `GET /ai/ready` → internal `GET /ready`

Set `BEHIND_GATEWAY=True` for correct rate limiting via `X-Forwarded-For`.

---

## Configuration

See [ENV_VARS.md](./ENV_VARS.md) for the complete environment variable reference.

Key settings for the AI service:

| Variable | Default | Purpose |
|---|---|---|
| `QDRANT_URL` | `http://localhost:6333` | Qdrant endpoint |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `JWT_SECRET` | — | Shared secret with Node.js API |
| `JWT_EXPIRES` | `7d` | JWT expiration duration (e.g. `7d`, `24h`, `60m`) |
| `SIMILARITY_THRESHOLD` | `0.65` | Minimum confidence for face match |
| `MAX_IMAGE_SIZE_BYTES` | `5242880` | Max upload size (5 MB) |
| `BEHIND_GATEWAY` | `True` | Respect `X-Forwarded-For` headers |

---

## Security

1. **Image validation** — Content type restricted to `image/jpeg` and `image/png`; size capped at 5 MB
2. **Rate limiting** — Per-endpoint limits (register: 10/min, login: 5/min, delete: 30/min, bulk delete: 10/min); respects `X-Forwarded-For` behind a gateway
3. **JWT authentication** — Required for all mutation endpoints (register, delete)
4. **Ownership enforcement** — Single-point delete verifies JWT `userId` matches the point's `user_id` payload
5. **Threshold-based rejection** — `score_threshold` enforced at Qdrant query level (0.65 minimum cosine similarity)
6. **Safe error messages** — Custom `FaceDetectionError` returns user-safe messages, never raw stack traces

---

## Known Gaps & Future Work

1. **`workers/deletion_worker.py`** — empty. Should consume Redis stream `mrayti_events` to handle "user deleted" events and remove all face vectors for a deleted user from Qdrant.
2. **No batch registration** — each face pose requires a separate HTTP call.
3. **Face count endpoint** — `GET /faces/count` uses Qdrant's `count()` API which is already efficient, but caching could be added for high-traffic scenarios.
