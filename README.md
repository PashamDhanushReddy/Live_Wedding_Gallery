# Wedding Live Photos

A production-quality web application for sharing live wedding photos with guests, featuring automated face recognition, a live gallery, and a TV/projector display mode.

## Architecture

*   **Frontend**: Next.js (App Router), React, Tailwind CSS, Framer Motion.
*   **Backend**: Django, Django REST Framework, Django Channels (WebSockets).
*   **Database**: PostgreSQL (Data), Redis (Message Broker & Cache).
*   **Storage**: Cloudinary (Multi-account storage manager for up to 100GB).
*   **Background Workers**: Celery (Face recognition, GDPR compliance).
*   **Offline Uploader**: Standalone Python script with local SQLite queue and exponential backoff.
*   **Face Recognition**: DeepFace (Facenet).

## Features

1.  **Live Photo Gallery**: Real-time gallery updating instantly via WebSockets as the photographer uploads photos.
2.  **Your Photos**: Guests can upload a selfie and instantly see only the photos they are in, thanks to background face recognition.
3.  **TV / Projector Mode**: A dedicated, full-screen view (`/wedding/[slug]/tv`) for live venues that shows new photos as they arrive and falls back to a beautiful slideshow.
4.  **Offline Photographer Uploader**: A robust, standalone application that watches a local folder on the photographer's laptop and reliably uploads photos to the backend even on spotty venue Wi-Fi.
5.  **Multi-Account Cloudinary Manager**: Seamlessly pools multiple 25GB Cloudinary accounts into a single large storage volume with automated failover and capacity management.

## Getting Started (Docker)

The easiest way to run the entire stack locally is using Docker Compose.

1.  Clone the repository.
2.  Set up environment variables in `backend/.env` (Cloudinary credentials).
3.  Run `docker-compose up --build`.
4.  Access the frontend at `http://localhost:3000`.
5.  Access the backend API at `http://localhost:8000`.

## Manual Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Celery Workers

```bash
cd backend
celery -A config worker -l info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Photographer Uploader

```bash
cd photographer-uploader
pip install requests
python uploader.py
```
(Place images in the `import` directory to queue them for upload).

## GDPR & Privacy

The system automatically deletes guest session data and face embeddings after 30 days to comply with data protection regulations. The `delete_expired_guests` Celery task handles this automatically.
