from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from django.conf.urls.static import static

def health_check(request):
    """
    Production health check probing:
    1. Django application process alive
    2. NeonDB PostgreSQL connection readiness
    3. Redis connectivity (if REDIS_URL configured)
    Returns HTTP 200 on healthy; HTTP 503 if critical dependencies are down.
    """
    from django.db import connection
    status_report = {
        "status": "healthy",
        "service": "live-wedding-gallery-backend",
        "timestamp": timezone.now().isoformat(),
        "database": "unknown",
        "redis": "disabled"
    }

    # 1. Probe database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        status_report["database"] = "connected"
    except Exception as db_err:
        status_report["status"] = "degraded"
        status_report["database"] = f"unhealthy: {str(db_err)[:100]}"

    # 2. Probe Redis (if configured)
    redis_url = getattr(settings, 'REDIS_URL', None)
    if redis_url:
        try:
            import redis
            client = redis.from_url(redis_url, socket_timeout=2)
            client.ping()
            status_report["redis"] = "connected"
        except Exception as redis_err:
            status_report["status"] = "degraded"
            status_report["redis"] = f"unhealthy: {str(redis_err)[:100]}"

    http_status = 200 if status_report["database"] == "connected" else 503
    return JsonResponse(status_report, status=http_status)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    path('api/observability/', include('observability.urls')),
    path('api/weddings/', include('weddings.urls')),
    path('api/weddings/<slug:slug>/photographer/', include('photos.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
