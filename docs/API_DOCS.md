# Mrayti AI Biometrics Service — API Documentation

Base URL: `http://<host>:8000`

All secure endpoints require a JWT in the `Authorization` header:
```
Authorization: Bearer <your_jwt_token>
```

---

## POST /ai/register — Register Face Pose

Registers a facial embedding for the authenticated user. Call multiple times during onboarding to capture different angles.

**Rate limit:** 10 requests/min

**Headers:**
| Header | Required | Notes |
|--------|----------|-------|
| `Authorization: Bearer <token>` | Yes | JWT from login |
| `Content-Length` | No | Used for size validation |

**Body:** `multipart/form-data`
| Field | Type | Max size | Accepted formats |
|-------|------|----------|------------------|
| `file` | image | 5 MB | `.jpg`, `.jpeg`, `.png` |

**Response `201 Created`:**
```json
{
  "success": true,
  "message": "Face vector successfully registered.",
  "point_id": "b8a9c2d0-...",
  "user_id": "user_123"
}
```

**Errors:**
| Status | Detail |
|--------|--------|
| 400 | Invalid image type. Only JPEG and PNG are allowed. |
| 401 | Not authenticated (missing/expired/invalid JWT) |
| 422 | No face detected in the image |
| 429 | Rate limit exceeded |
| 413 | Image too large (over 5 MB) |

---

## POST /ai/login — Face Login (Biometric Auth)

Authenticates a user by matching their face against stored vectors. On success, returns a signed JWT.

**Rate limit:** 5 requests/min

**Body:** `multipart/form-data`
| Field | Type | Max size | Accepted formats |
|-------|------|----------|------------------|
| `file` | image | 5 MB | `.jpg`, `.jpeg`, `.png` |

**Response `200 OK`:**
```json
{
  "ok": true,
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "userId": "6a3b1a6a75b4fd165ed0da44"
}
```
The token is signed with the shared `JWT_SECRET` and expires per `JWT_EXPIRES` (default 7 days).

**Errors:**
| Status | Detail |
|--------|--------|
| 400 | Invalid image type |
| 401 | Face not recognized (confidence below 0.65 threshold) |
| 422 | No face detected in the image |
| 429 | Rate limit exceeded |

---

## DELETE /ai/faces/{point_id} — Delete Face Point

Deletes a single registered face vector by its UUID. The authenticated user can only delete their own vectors.

**Rate limit:** 30 requests/min

**Headers:**
| Header | Required |
|--------|----------|
| `Authorization: Bearer <token>` | Yes |

**Response `200 OK`:**
```json
{
  "success": true,
  "message": "Face vector successfully deleted.",
  "point_id": "b8a9c2d0-..."
}
```

**Errors:**
| Status | Detail |
|--------|--------|
| 401 | Not authenticated |
| 403 | Point belongs to a different user |
| 404 | No face vector found with the given point ID |

---

## DELETE /ai/faces/user/{user_id} — Delete All User Faces

Deletes all face vectors for the authenticated user. The `user_id` path param must match the JWT's `userId`.

**Rate limit:** 10 requests/min

**Headers:**
| Header | Required |
|--------|----------|
| `Authorization: Bearer <token>` | Yes |

**Response `200 OK`:**
```json
{
  "success": true,
  "message": "Successfully deleted 3 face vector(s).",
  "deleted_count": 3
}
```

**Errors:**
| Status | Detail |
|--------|--------|
| 401 | Not authenticated |
| 403 | Target `user_id` does not match authenticated user |
| 404 | No face vectors found for this user |

---

## GET /ai/faces/count — Check Face Registration Status

Returns the number of face vectors registered for the authenticated user and whether any exist. Useful for the frontend to determine if a user already has face data before showing the registration UI.

**Rate limit:** 30 requests/min

**Headers:**
| Header | Required |
|--------|----------|
| `Authorization: Bearer <token>` | Yes |

**Response `200 OK`:**
```json
{
  "user_id": "6a3b1a6a75b4fd165ed0da44",
  "count": 3,
  "exists": true
}
```

**Errors:**
| Status | Detail |
|--------|--------|
| 401 | Not authenticated |

---

## GET /ai/health — Liveness Probe

Returns OK if the container process is running. Used by Docker orchestrator.

**Response `200 OK`:**
```json
{
  "status": "alive"
}
```

---

## GET /ai/ready — Readiness Probe

Returns OK only if Qdrant and Redis are reachable.

**Response `200 OK`:**
```json
{
  "status": "ready",
  "qdrant": "connected",
  "redis": "connected"
}
```

**Response `503 Service Unavailable`:**
```json
{
  "status": "unready",
  "dependencies": {
    "qdrant": "Unreachable or initializing",
    "redis": "Ping failed"
  }
}
```
