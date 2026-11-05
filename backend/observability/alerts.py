"""
Actionable Production Alerting Engine for Live Wedding Gallery.
Evaluates metrics against operational thresholds and produces structured,
prioritized alerts with concrete remediation procedures.
"""

from typing import List, Dict, Any
from .metrics import metrics


class AlertEngine:
    """Evaluates real-time system state and raises actionable alerts."""

    @classmethod
    def evaluate_active_alerts(cls) -> List[Dict[str, Any]]:
        alerts = []
        snap = metrics.get_all_metrics()

        # ----------------------------------------------------------------------
        # 1. Database Connectivity Alert (CRITICAL)
        # ----------------------------------------------------------------------
        db_stat = snap.get('database', {}).get('status')
        if db_stat != 'CONNECTED':
            alerts.append({
                'id': 'DB_CONNECTION_FAILURE',
                'severity': 'CRITICAL',
                'title': 'NeonDB Connection Failure',
                'metric': f"Status: {db_stat}",
                'threshold': 'CONNECTED',
                'description': 'The Django backend cannot communicate with NeonDB PostgreSQL. Gallery queries and intake are blocked.',
                'action': 'Check NeonDB status dashboard, verify DATABASE_URL credentials, and check if Neon scaled-to-zero or exhausted pooler slots.'
            })

        # ----------------------------------------------------------------------
        # 2. Dead-Letter Ingestion Jobs (CRITICAL)
        # ----------------------------------------------------------------------
        dl_count = snap.get('queue', {}).get('dead_letter_count', 0)
        if dl_count > 0:
            alerts.append({
                'id': 'INGESTION_DEAD_LETTER',
                'severity': 'CRITICAL',
                'title': f'{dl_count} Dead-Letter Ingestion Jobs Detected',
                'metric': f"{dl_count} jobs dead-lettered",
                'threshold': '0 dead-letter jobs',
                'description': 'Photos have permanently failed all 5 processing retries and are stranded in DEAD_LETTER status.',
                'action': 'Visit /api/observability/trace/ or admin dashboard. Inspect dead_letter_reason, resolve Cloudinary or staging issues, and click Retry Dead-Letters.'
            })

        # ----------------------------------------------------------------------
        # 3. Ingestion Queue Stalled (CRITICAL / WARNING)
        # ----------------------------------------------------------------------
        oldest_age = snap.get('queue', {}).get('oldest_job_age_seconds', 0.0)
        backlog = snap.get('queue', {}).get('backlog_count', 0)
        if oldest_age > 180.0 and backlog > 0:
            alerts.append({
                'id': 'QUEUE_PROCESSING_STALLED',
                'severity': 'CRITICAL',
                'title': 'Upload Processing Pipeline Stalled',
                'metric': f"Oldest job age: {oldest_age:.0f}s, Backlog: {backlog}",
                'threshold': '< 120s max job age',
                'description': 'Photos are entering the queue but background workers are not completing them in a timely manner.',
                'action': 'Check Celery worker container logs on Render, verify Redis broker connectivity, and check for hung Cloudinary upload threads.'
            })
        elif backlog > 40:
            alerts.append({
                'id': 'QUEUE_BACKLOG_HIGH',
                'severity': 'WARNING',
                'title': f'High Ingestion Backlog ({backlog} photos queued)',
                'metric': f"Backlog count: {backlog}",
                'threshold': '< 40 in-flight jobs',
                'description': 'Incoming photos from photographer burst shooting are outpacing worker concurrency.',
                'action': 'Scale up Celery worker concurrency or spin up an additional worker instance.'
            })

        # ----------------------------------------------------------------------
        # 4. API Error Rate (CRITICAL / WARNING)
        # ----------------------------------------------------------------------
        err_rate = snap.get('api', {}).get('error_rate_percent', 0.0)
        if err_rate > 5.0:
            alerts.append({
                'id': 'API_ERROR_RATE_HIGH',
                'severity': 'CRITICAL',
                'title': f'Elevated API Error Rate ({err_rate}% 5xx)',
                'metric': f"{err_rate}% requests returning 5xx",
                'threshold': '< 5.0% error rate',
                'description': 'A high percentage of visitor or photographer requests are failing with server 500 errors.',
                'action': 'Check structured error logs via /api/observability/metrics/ or Render logs. Check database query timeouts or syntax exceptions.'
            })
        elif err_rate > 1.5:
            alerts.append({
                'id': 'API_ERROR_RATE_ELEVATED',
                'severity': 'WARNING',
                'title': f'Elevated API Error Rate ({err_rate}%)',
                'metric': f"{err_rate}% 5xx responses",
                'threshold': '< 1.5% error rate',
                'description': 'Intermittent 5xx errors detected on API endpoints.',
                'action': 'Inspect recent traceback logs for specific route failures.'
            })

        # ----------------------------------------------------------------------
        # 5. Cloudinary Upload Failure Rate (CRITICAL / WARNING)
        # ----------------------------------------------------------------------
        cld_fail_rate = snap.get('cloudinary', {}).get('failure_rate_percent', 0.0)
        cld_tot = snap.get('cloudinary', {}).get('uploads_total', 0)
        if cld_tot >= 5 and cld_fail_rate > 20.0:
            alerts.append({
                'id': 'CLOUDINARY_UPLOAD_FAILS',
                'severity': 'CRITICAL',
                'title': f'Cloudinary Upload Failure Rate ({cld_fail_rate}%)',
                'metric': f"{cld_fail_rate}% failed uploads",
                'threshold': '< 10% upload failures',
                'description': f"Cloudinary CDN uploads are failing. Last error: {snap.get('cloudinary', {}).get('last_error')}",
                'action': 'Verify Cloudinary account status, check if credit quota or file size limit was reached, or check egress network from Render.'
            })

        # ----------------------------------------------------------------------
        # 6. Cloudinary Credit Quota Warning
        # ----------------------------------------------------------------------
        usage = snap.get('cloudinary', {}).get('account_usage', {})
        credits_pct = usage.get('credits', {}).get('used_percent', 0.0)
        if isinstance(credits_pct, (int, float)) and credits_pct > 80.0:
            alerts.append({
                'id': 'CLOUDINARY_CREDITS_LOW',
                'severity': 'WARNING',
                'title': f'Cloudinary Credits at {credits_pct}% of Plan Limit',
                'metric': f"{credits_pct}% credits used",
                'threshold': '< 80% credit usage',
                'description': 'Cloudinary credit usage is nearing monthly allocation.',
                'action': 'Review Cloudinary transformations, optimize image cache headers, or upgrade Cloudinary tier before the event.'
            })

        # ----------------------------------------------------------------------
        # 7. Memory High (WARNING / CRITICAL)
        # ----------------------------------------------------------------------
        mem_pct = snap.get('system', {}).get('memory_system_used_percent', 0.0)
        mem_rss = snap.get('system', {}).get('memory_process_rss_mb', 0.0)
        if mem_pct > 90.0 or mem_rss > 480.0:
            alerts.append({
                'id': 'SYSTEM_RAM_CRITICAL',
                'severity': 'CRITICAL',
                'title': f'Critical RAM Usage ({mem_pct}% / {mem_rss:.0f} MB)',
                'metric': f"Process RSS: {mem_rss:.0f} MB",
                'threshold': '< 450 MB RSS',
                'description': 'Process RAM is approaching container limit (512MB standard on Render Starter). Risk of OOM kill.',
                'action': 'Verify Pillow and InsightFace image buffers are being garbage-collected. Avoid processing multiple RAW photos concurrently.'
            })

        # ----------------------------------------------------------------------
        # 8. Android Companion Ingestion Device Inactivity / Low Storage
        # ----------------------------------------------------------------------
        devices = snap.get('android_ingestion', {}).get('devices', [])
        for dev in devices:
            if dev.get('is_low_storage'):
                alerts.append({
                    'id': f"ANDROID_LOW_DISK_{dev.get('device_id')}",
                    'severity': 'CRITICAL',
                    'title': f"Android Device {dev.get('device_id')} Low Storage (<1GB)",
                    'metric': f"Storage used: {dev.get('storage_usage_mb')} MB",
                    'threshold': '> 1GB free storage',
                    'description': f"The companion phone running FTP server is nearly out of storage space.",
                    'action': 'Trigger safe cleanup in the companion app: purge verified FORWARDED files from ready_photos.'
                })
            if dev.get('ftp_status') == 'ERROR':
                alerts.append({
                    'id': f"ANDROID_FTP_ERROR_{dev.get('device_id')}",
                    'severity': 'CRITICAL',
                    'title': f"FTP Server Error on {dev.get('device_id')}",
                    'metric': 'FTP status: ERROR',
                    'threshold': 'RUNNING',
                    'description': 'The FTP server on the photographer companion phone stopped unexpectedly.',
                    'action': 'Open companion app, check Wi-Fi tethering / hotspot IP, and toggle Start FTP Server.'
                })

        # ----------------------------------------------------------------------
        # 9. Database Growth Anomaly (WARNING)
        # ----------------------------------------------------------------------
        growth = snap.get('database_growth', {})
        if growth.get('growth_anomaly_detected'):
            alerts.append({
                'id': 'DB_GROWTH_SURGE',
                'severity': 'WARNING',
                'title': 'Rapid Database Growth Surge Detected',
                'metric': f"{growth.get('photos_added_last_hour')} photos added in last hour",
                'threshold': '< 1000 photos / hour',
                'description': 'Abnormal volume of photos being registered in the database.',
                'action': 'Verify photographer camera connection to ensure duplicate loop is not occurring.'
            })

        return alerts

