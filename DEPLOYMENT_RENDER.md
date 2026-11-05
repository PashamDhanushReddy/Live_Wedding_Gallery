# Render Production Deployment & Architecture Runbook
**Live Wedding Gallery — Production Cloud Infrastructure**

---

## 1. Architecture Overview

The Live Wedding Gallery backend is decoupled into three dedicated services on Render, connected to external managed services for database and media storage:

```
                                  +---------------------------------------+
                                  |         React Frontend                |
                                  |  (GitHub Pages / Render Static Site)  |
                                  +---------------------------------------+
                                           |                      |
                        REST APIs & HTTPS  |                      | Cloudinary CDN Images
                                           v                      v
+------------------------+        +-----------------------------------------------+
|  Android Companion App | ---->  |   live-wedding-web (Render Web Service)       |
|  (Photographer Phone)  | HTTPS  |   - Daphne ASGI Server (HTTP & WebSockets)    |
+------------------------+        |   - Immediate HTTP 202 Accepted (<200ms)      |
                                  +-----------------------------------------------+
                                           |                     |
                                           | Enqueue Jobs        | Broadcast Events
                                           v                     v
                                  +-----------------------------------------------+
                                  |   live-wedding-redis (Render Redis)           |
                                  |   - Django Channels Real-Time Broadcasts      |
                                  |   - Celery Asynchronous Job Queue             |
                                  +-----------------------------------------------+
                                           ^
                                           | Consume Tasks
                                           v
                                  +-----------------------------------------------+
                                  |   live-wedding-worker (Render Background)     |
                                  |   - Celery Worker (concurrency: 2)            |
                                  |   - Cloudinary CDN Ingestion                  |
                                  |   - InsightFace (buffalo_sc) ONNX Inference   |
                                  +-----------------------------------------------+
                                           |
                                           +--------------+
                                           |              |
                                           v              v
                        +----------------------+    +--------------------------+
                        |   NeonDB PostgreSQL  |    |   Cloudinary CDN         |
                        |   - PgBouncer Pooler |    |   - Original Asset Store |
                        |   - pgvector HNSW    |    |   - Dynamic Transformations|
                        +----------------------+    +--------------------------+
```

---

## 2. Service Separation & Compute Roles

### Service 1: `live-wedding-web` (Web Service)
- **Type**: `web`
- **Engine**: `daphne -b 0.0.0.0 -p $PORT config.asgi:application`
- **Role**:
  - Serves HTTP REST API endpoints (`/api/weddings/...`).
  - Maintains 500+ persistent WebSocket connections for real-time guest updates.
  - Receives chunked photo uploads from photographer Android phone / Web Dashboard.
  - Streams upload to ephemeral `/tmp/staging` buffer, validates magic bytes & checksum, and commits `IngestionJob` record.
  - Returns **`HTTP 202 Accepted`** within ~150ms.
  - Dispatches job to Celery Redis queue.
  - **Memory Profile**: ~150–220 MB RAM (Zero ONNX / ML model overhead).
  - **CPU Profile**: Low (<15% during peak traffic).

### Service 2: `live-wedding-worker` (Background Worker Service)
- **Type**: `worker`
- **Engine**: `celery -A config worker -l info --concurrency=2`
- **Role**:
  - Pulls queued jobs from Redis (`task_default_queue='ingestion'`).
  - Uploads photo directly to Cloudinary and purges local staging file immediately.
  - Downloads 1200px preview from Cloudinary CDN.
  - Executes InsightFace (`buffalo_sc`) neural network inference to detect all faces and extract 512-dimensional normalized embeddings.
  - Writes face records to NeonDB using `pgvector`.
  - Publishes `new_photo` notification to Redis Channels layer for real-time delivery.
  - **Memory Profile**: ~500–650 MB RAM (ONNX Runtime + InsightFace model weights).
  - **CPU Profile**: High burst during photo batches (100% of 1 core during inference).

### Service 3: `live-wedding-redis` (Private Redis Broker)
- **Type**: `redis`
- **Plan**: `starter` (256 MB)
- **Role**:
  - Celery message broker (`CELERY_BROKER_URL`).
  - Django Channels ASGI channel layer (`channels_redis.core.RedisChannelLayer`).
  - Restricted to Render internal private network (`ipAllowList: []`).

---

## 3. Storage Analysis & Disk Policy

| Service / Resource | Storage Type | Retention Policy | Notes |
| :--- | :--- | :--- | :--- |
| **Web Service (`live-wedding-web`)** | Ephemeral `/tmp` | Purged on upload | **NO persistent disk needed.** Staging files deleted immediately upon Cloudinary receipt. |
| **Worker (`live-wedding-worker`)** | Ephemeral | Purged on completion | **NO persistent disk needed.** Pulls previews directly from Cloudinary CDN. |
| **Original High-Res Photographs** | Cloudinary CDN | Permanent | 100% cloud object storage. Zero local disk dependency on Render. |
| **Job Queue & State** | NeonDB PostgreSQL | Durable | All job checkpoints (`RECEIVED`, `QUEUED`, `CLOUDINARY_COMPLETED`, `DB_REGISTERED`, `FACE_PROCESSING`, `COMPLETED`) persist in NeonDB. |
| **Message Broker** | Render Redis | In-Memory (LRU) | Volatile message passing only. |

---

## 4. Capacity Assessment: Free Tier vs. Paid Plans

> [!WARNING]
> **Free Tier Feasibility Assessment**: The Render Free Tier is **unsuitable for 500 simultaneous users and real-time wedding photography**.
> 1. **512 MB RAM Ceiling**: InsightFace (`buffalo_sc`) + ONNX Runtime + Django consumes ~550 MB RAM. On the free tier, the process is killed instantly by the Linux OOM (Out Of Memory) killer (`SIGKILL`).
> 2. **Inactivity Sleep**: Free instances spin down after 15 minutes of inactivity and take 50+ seconds to spin up, causing camera ingestion timeouts.
> 3. **No Background Worker**: Background workers (`type: worker`) are only available on paid plans.
> 4. **CPU Throttling**: Free CPU shares (0.1 vCPU) make face extraction take 25–40 seconds per photo instead of 1.2 seconds.

### Recommended Production Tier (500 Concurrent Users & Live Ingestion)

| Service | Recommended Plan | Spec | Estimated Monthly Cost |
| :--- | :--- | :--- | :--- |
| `live-wedding-web` | **Standard** (or Starter) | 1 vCPU, 2 GB RAM | $25 / mo ($7 on Starter) |
| `live-wedding-worker`| **Standard** | 1 vCPU, 2 GB RAM | $25 / mo |
| `live-wedding-redis` | **Starter** | 256 MB RAM | $7 / mo |
| **Total** | | | **~$39 – $57 / mo** |

*Tip: For an active wedding weekend, run both on **Standard**, then scale down to **Starter** or pause the worker service after the event.*

---

## 5. Environment Variables Configuration

Configure these environment variables in your Render Blueprint or Dashboard:

| Key | Example Value | Source / Security |
| :--- | :--- | :--- |
| `DEBUG` | `false` | Explicitly `false` in production |
| `DJANGO_SETTINGS_MODULE` | `config.settings` | Configuration module |
| `PYTHON_VERSION` | `3.11.0` | Production runtime |
| `SECRET_KEY` | *(Render auto-generated)* | Cryptographic key |
| `DATABASE_URL` | `postgresql://user:pass@ep-...-pooler...neon.tech/neondb?sslmode=require` | Secret (NeonDB pgBouncer connection string) |
| `REDIS_URL` | *(Render Redis connectionString)* | Internal Render service mesh |
| `USE_REDIS_CHANNEL_LAYER` | `true` | Enables Redis Channels layer |
| `CLOUDINARY_CLOUD_NAME` | `xfebr0cj` | Secret |
| `CLOUDINARY_API_KEY` | `631855912397358` | Secret |
| `CLOUDINARY_API_SECRET` | `2OVYq7m...` | Secret (Backend only; never exposed to React or Android) |
| `FACE_MODEL_NAME` | `buffalo_sc` | Compact InsightFace model |
| `FACE_MATCH_THRESHOLD` | `0.45` | Cosine similarity threshold |

---

## 6. Health Checks, Graceful Shutdown & Recovery

### Health Check Endpoint
- **URL**: `GET /api/health/`
- **Behavior**:
  - Executes `SELECT 1` against NeonDB PostgreSQL.
  - Pings Render Redis broker.
  - Returns `HTTP 200 OK` when healthy.
  - Returns `HTTP 503 Service Unavailable` if database is down, prompting Render to avoid routing traffic to an unhealthy instance.

### Graceful Termination
- Render sends `SIGTERM` before restarting or deploying.
- **Celery**: Configured with `task_acks_late=True` and `task_reject_on_worker_lost=True`. If the container restarts mid-task, unacknowledged jobs are safely re-queued in Redis.
- **Daphne**: Finishes in-flight HTTP requests and cleanly closes WebSocket connections with status code `1001 (Going Away)`. The React client's exponential reconnect loop automatically reconnects within 2 seconds.
- **Application Startup**: `resume_interrupted_jobs()` runs on startup and re-enqueues any uncompleted `IngestionJob` records found in NeonDB.

---

## 7. Deployment & Rollback Runbook

### Initial Deployment via Blueprint (Recommended)
1. Commit and push all changes to your GitHub / GitLab repository.
2. Log in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** -> **Blueprint**.
4. Select your repository `Live_Wedding_Gallery`.
5. Render detects the root `render.yaml` and displays:
   - `live-wedding-web` (Web Service)
   - `live-wedding-worker` (Background Worker)
   - `live-wedding-redis` (Redis Instance)
6. Enter the secret environment variables (`DATABASE_URL`, `CLOUDINARY_*`).
7. Click **Apply**.
8. Render builds the services using `./build.sh` (which automatically runs `pip install`, `python manage.py migrate`, and `python manage.py collectstatic`).

### Zero-Downtime Updates
Every push to `main` automatically triggers Render's rolling deployment:
1. Render spins up the new container in the background.
2. Render executes `./build.sh`.
3. Render probes `/api/health/`.
4. Only when `/api/health/` returns `200`, Render swaps the traffic router and drains the old container.

### Rollback Runbook
If an issue occurs after deployment:
1. **Instant UI Rollback**:
   - Go to `live-wedding-web` -> **Deploys**.
   - Find the previous healthy deploy and click **Rollback**.
   - Do the same for `live-wedding-worker`.
2. **Git Revert Rollback**:
   ```bash
   git revert HEAD
   git push origin main
   ```
3. **Database Safeguard**:
   - NeonDB provides instant point-in-time recovery and branch restoration if a migration needs to be rolled back.

