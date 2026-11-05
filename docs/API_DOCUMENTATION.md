# REST API & WebSocket Specification
**Live Wedding Gallery — Production API Documentation**

This document provides complete reference documentation for all HTTP REST endpoints and real-time WebSocket channels available in the Live Wedding Gallery backend.

---

## 1. Authentication & Security Headers

### 1.1 Authentication Schemes
1. **Anonymous Guest Access**:
   - Public read endpoints (`/api/weddings/<slug>/photos/`) and selfie search (`/api/weddings/<slug>/search/`) do not require authentication.
   - Throttled automatically to prevent denial of service (120 req/min for general reads, 15 req/min for selfie searches).
2. **Token Authentication (Photographers & Companion App)**:
   - Required for photographer ingestion, device synchronization, and job management endpoints.
   - Pass in HTTP Authorization header:
     ```http
     Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
     ```
3. **Session Authentication (Admins)**:
   - Used for Django Admin and the `/admin/live` Real-Time Observability Monitor.

### 1.2 Common Response Headers
* `X-Correlation-ID`: Unique correlation UUID traced across logs and workers.
* `X-RateLimit-Limit`: Maximum allowable requests per minute for the route.
* `X-RateLimit-Remaining`: Remaining requests before rate limiting kicks in.
* `Content-Type`: `application/json` (unless downloading or redirecting).

---

## 2. System Health & Observability Endpoints

### 2.1 Service Health Check
```http
GET /api/health/
```
* **Authentication**: None
* **Description**: Verifies Django process readiness, NeonDB connection, and Redis connectivity.
* **Response (HTTP 200 OK)**:
  ```json
  {
    "status": "healthy",
    "service": "live-wedding-gallery-backend",
    "timestamp": "2026-11-05T06:58:00.000000Z",
    "database": "connected",
    "redis": "connected"
  }
  ```

---

### 2.2 Live Observability Dashboard
```http
GET /api/observability/dashboard/
```
* **Authentication**: Admin Session or Token Auth
* **Description**: Aggregates comprehensive system telemetry: active WebSocket connections, queue depths, Cloudinary quota, database latency, and node health.
* **Response (HTTP 200 OK)**:
  ```json
  {
    "summary": {
      "active_websockets": 412,
      "pending_ingestion_jobs": 3,
      "failed_dead_letters": 0,
      "total_photos": 6420,
      "avg_api_latency_ms": 38.2,
      "status": "HEALTHY"
    },
    "cloudinary": {
      "plan": "Production",
      "credits_used_percent": 14.8,
      "storage_gb": 32.4,
      "bandwidth_gb": 48.1
    },
    "system": {
      "instance_id": "live-wedding-web-7f89b",
      "cpu_percent": 12.4,
      "memory_mb": 184.2
    }
  }
  ```

---

### 2.3 End-to-End Photo Lifecycle Tracer
```http
GET /api/observability/trace/?id=<FILENAME_OR_CHECKSUM_OR_JOB_ID>
```
* **Description**: Traces a single photograph step-by-step from camera FTP reception to gallery publication.
* **Response (HTTP 200 OK)**:
  ```json
  {
    "query": "ceremony_kiss.jpg",
    "matched": true,
    "photo_id": 501,
    "current_status": "COMPLETED",
    "milestones": [
      {
        "stage": "CAMERA_FTP_RECEIVED",
        "timestamp": "2026-11-05T14:20:00Z",
        "details": "Transferred to Android ready_photos/ folder"
      },
      {
        "stage": "HTTP_INGESTION_ACCEPTED",
        "timestamp": "2026-11-05T14:20:01Z",
        "details": "Job UUID 24a11c7d-5484-4e1c-b39f-ceb369f31cd8 committed (HTTP 202)"
      },
      {
        "stage": "CLOUDINARY_UPLOADED",
        "timestamp": "2026-11-05T14:20:02Z",
        "details": "Public ID weddings/sandeep-prathyusha/Ceremony/2026-11-05/da1fd7"
      },
      {
        "stage": "FACE_EMBEDDINGS_EXTRACTED",
        "timestamp": "2026-11-05T14:20:03Z",
        "details": "InsightFace detected 4 faces; indexed in pgvector"
      },
      {
        "stage": "WEBSOCKET_BROADCASTED",
        "timestamp": "2026-11-05T14:20:03Z",
        "details": "Published to group wedding_sandeep-prathyusha"
      }
    ]
  }
  ```

---

## 3. Public Guest Gallery Endpoints

### 3.1 Wedding Overview & Metadata
```http
GET /api/weddings/<slug:slug>/
```
* **Response (HTTP 200 OK)**:
  ```json
  {
    "slug": "sandeep-prathyusha",
    "bride_name": "Prathyusha",
    "groom_name": "Sandeep",
    "wedding_title": "Sandeep & Prathyusha's Wedding",
    "wedding_date": "2026-11-21",
    "venue": "Grand Palace Convention Center",
    "cover_image": "https://res.cloudinary.com/xfebr0cj/image/upload/v1/weddings/cover.jpg",
    "is_active": true
  }
  ```

---

### 3.2 Paginated Gallery Photos
```http
GET /api/weddings/<slug:slug>/photos/?page=1&page_size=30&folder=Ceremony
```
* **Query Parameters**:
  * `page` (int, default: 1): Page number.
  * `page_size` (int, default: 30, max: 100): Photos per page.
  * `folder` (string, optional): Filter by folder name (`All`, `Ceremony`, `Reception`, `Guests`, `Decor`).
* **Response (HTTP 200 OK)**:
  ```json
  {
    "count": 6420,
    "next": "https://.../api/weddings/sandeep-prathyusha/photos/?page=2",
    "previous": null,
    "results": [
      {
        "id": 501,
        "original_filename": "DSC01928.JPG",
        "thumbnail_url": "https://res.cloudinary.com/xfebr0cj/image/upload/c_scale,w_400,q_auto,f_auto/v1/weddings/sandeep-prathyusha/Ceremony/2026-11-05/da1fd7",
        "preview_url": "https://res.cloudinary.com/xfebr0cj/image/upload/c_limit,w_1200,h_1200,q_auto,f_auto/v1/weddings/sandeep-prathyusha/Ceremony/2026-11-05/da1fd7",
        "large_preview_url": "https://res.cloudinary.com/xfebr0cj/image/upload/c_limit,w_2000,h_2000,q_auto,f_auto/v1/weddings/sandeep-prathyusha/Ceremony/2026-11-05/da1fd7",
        "width": 6000,
        "height": 4000,
        "folder": "Ceremony",
        "created_at": "2026-11-05T14:20:00Z"
      }
    ]
  }
  ```

---

### 3.3 Direct High-Res Photo Download
```http
GET /api/weddings/<slug:slug>/photos/<int:pk>/download/
```
* **Description**: Returns an immediate **HTTP 302 Found** redirecting directly to the Cloudinary CDN asset with `fl_attachment:<filename>`. Render never streams large binaries.
* **Response (HTTP 302 Found)**:
  ```http
  Location: https://res.cloudinary.com/xfebr0cj/image/upload/fl_attachment:DSC01928.JPG/v1/weddings/sandeep-prathyusha/Ceremony/2026-11-05/da1fd7.jpg
  ```

---

### 3.4 AI Facial Recognition ("Find My Photos")
```http
POST /api/weddings/<slug:slug>/search/
Content-Type: multipart/form-data
```
* **Form Parameters**:
  * `selfie`: Image binary (JPEG/PNG/WebP, max 10 MB).
* **Processing Flow**:
  1. Validates magic bytes & file constraints.
  2. InsightFace generates 512-d normalized probe vector.
  3. Executes pgvector cosine similarity search (`<->` operator) against `faces_face_emb_hnsw_idx`.
  4. Returns matched photo records with similarity confidence score.
* **Response (HTTP 200 OK)**:
  ```json
  {
    "matches_count": 14,
    "threshold": 0.45,
    "photos": [
      {
        "id": 501,
        "thumbnail_url": "https://res.cloudinary.com/...",
        "preview_url": "https://res.cloudinary.com/...",
        "large_preview_url": "https://res.cloudinary.com/...",
        "similarity_score": 0.892,
        "folder": "Ceremony"
      }
    ]
  }
  ```
* **Error Responses**:
  * `HTTP 400 Bad Request`: `{"error": "NO_FACE_DETECTED", "message": "No clear human face was detected in the submitted image."}`
  * `HTTP 429 Too Many Requests`: `{"error": "THROTTLED", "message": "Request was throttled. Expected available in 45 seconds."}`

---

## 4. Photographer & Edge Ingestion Endpoints

### 4.1 Photographer Authentication
```http
POST /api/weddings/<slug:slug>/login/
Content-Type: application/json

{
  "username": "photographer1",
  "password": "secret_password"
}
```
* **Response (HTTP 200 OK)**:
  ```json
  {
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
    "wedding": "sandeep-prathyusha",
    "user": "photographer1"
  }
  ```

---

### 4.2 Edge Companion Photo Upload
```http
POST /api/weddings/<slug:slug>/photographer/phone/upload/
Authorization: Token <TOKEN>
Content-Type: multipart/form-data
```
* **Form Fields**:
  * `photo`: File binary.
  * `device_id`: String (e.g. `pixel_7_cam1`).
  * `folder`: Category folder (e.g. `Ceremony`).
  * `checksum`: SHA-256 hex string (pre-computed by Android).
* **Response (HTTP 202 Accepted)**:
  ```json
  {
    "status": "ACCEPTED",
    "job_id": "24a11c7d-5484-4e1c-b39f-ceb369f31cd8",
    "upload_id": "pixel_7_cam1_1730791200",
    "message": "Photo accepted for asynchronous processing."
  }
  ```

---

### 4.3 Ingestion Job Status Query
```http
GET /api/weddings/<slug:slug>/photographer/jobs/<uuid:job_id>/
Authorization: Token <TOKEN>
```
* **Response (HTTP 200 OK)**:
  ```json
  {
    "job_id": "24a11c7d-5484-4e1c-b39f-ceb369f31cd8",
    "status": "COMPLETED",
    "original_filename": "DSC01928.JPG",
    "attempts": 1,
    "photo_id": 501,
    "cloudinary_public_id": "weddings/sandeep-prathyusha/Ceremony/2026-11-05/da1fd7",
    "created_at": "2026-11-05T14:20:01Z",
    "completed_at": "2026-11-05T14:20:03Z"
  }
  ```

---

## 5. Real-Time WebSocket Channel Specification

* **Protocol**: `WSS` (Secure WebSocket)
* **URL**: `wss://<HOST>/ws/wedding/<slug:slug>/`
* **Heartbeat**: Ping interval 30s (`{"type": "ping"}`); client returns `{"type": "pong"}`.

### 5.1 Event: `new_photo`
Dispatched automatically when a photo finishes ingestion and is ready for display.
```json
{
  "type": "new_photo",
  "photo": {
    "id": 501,
    "original_filename": "DSC01928.JPG",
    "thumbnail_url": "https://res.cloudinary.com/xfebr0cj/image/upload/c_scale,w_400,q_auto,f_auto/v1/weddings/sandeep-prathyusha/Ceremony/2026-11-05/da1fd7",
    "preview_url": "https://res.cloudinary.com/xfebr0cj/image/upload/c_limit,w_1200,h_1200,q_auto,f_auto/v1/weddings/sandeep-prathyusha/Ceremony/2026-11-05/da1fd7",
    "large_preview_url": "https://res.cloudinary.com/xfebr0cj/image/upload/c_limit,w_2000,h_2000,q_auto,f_auto/v1/weddings/sandeep-prathyusha/Ceremony/2026-11-05/da1fd7",
    "width": 6000,
    "height": 4000,
    "folder": "Ceremony",
    "created_at": "2026-11-05T14:20:00Z"
  }
}
```

### 5.2 Event: `delete_photo`
Dispatched when a photographer or administrator removes a photo.
```json
{
  "type": "delete_photo",
  "photo_id": 501
}
```

