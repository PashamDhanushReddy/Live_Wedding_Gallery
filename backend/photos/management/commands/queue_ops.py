"""
Operational management command for inspecting, monitoring, and managing the background
ingestion and processing queue for the Live Wedding Gallery.
"""

import os
import sys
import uuid
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from photos.models import IngestionJob, Photo
from photos.ingestion_service import enqueue_job
from photos.lock_utils import get_redis_client
from weddings.models import Wedding


class Command(BaseCommand):
    help = "Inspects background queue health, monitors job ages and failure rates, and retries failed or dead-letter jobs."

    def add_arguments(self, parser):
        parser.add_argument(
            '--inspect',
            action='store_true',
            help='Display queue health, in-flight counts, oldest job age, and failure rates.',
        )
        parser.add_argument(
            '--inspect-dead-letter',
            action='store_true',
            help='List dead-letter jobs with failure reasons and error stack details.',
        )
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Re-enqueue all FAILED jobs into the processing queue.',
        )
        parser.add_argument(
            '--retry-dead-letter',
            action='store_true',
            help='Reset retry attempts and re-enqueue DEAD_LETTER jobs into the processing queue.',
        )
        parser.add_argument(
            '--retry-job',
            type=str,
            help='Re-enqueue a specific IngestionJob by UUID.',
        )
        parser.add_argument(
            '--purge-dead-letter',
            action='store_true',
            help='Purge DEAD_LETTER job records older than the specified retention window.',
        )
        parser.add_argument(
            '--older-than-days',
            type=int,
            default=14,
            help='Retention window in days for purging dead-letter jobs (default: 14 days).',
        )
        parser.add_argument(
            '--wedding',
            type=str,
            help='Filter queue operations by specific wedding slug.',
        )

    def handle(self, *args, **options):
        wedding_slug = options.get('wedding')
        wedding = None
        if wedding_slug:
            wedding = Wedding.objects.filter(slug=wedding_slug).first()
            if not wedding:
                self.stderr.write(self.style.ERROR(f"Wedding '{wedding_slug}' not found."))
                return

        if options.get('inspect'):
            self.inspect_queue(wedding)
        elif options.get('inspect_dead_letter'):
            self.inspect_dead_letter(wedding)
        elif options.get('retry_failed'):
            self.retry_failed_jobs(wedding)
        elif options.get('retry_dead_letter'):
            self.retry_dead_letter_jobs(wedding)
        elif options.get('retry_job'):
            self.retry_specific_job(options['retry_job'])
        elif options.get('purge_dead_letter'):
            self.purge_dead_letter_jobs(options['older_than_days'], wedding)
        else:
            self.inspect_queue(wedding)

    def inspect_queue(self, wedding=None):
        self.stdout.write(self.style.NOTICE("=" * 65))
        self.stdout.write(self.style.NOTICE("   LIVE WEDDING GALLERY - BACKGROUND QUEUE MONITOR"))
        self.stdout.write(self.style.NOTICE("=" * 65))

        # 1. Broker connectivity
        redis_client = get_redis_client()
        if redis_client:
            try:
                redis_info = redis_client.info()
                redis_status = self.style.SUCCESS(f"Connected (Redis v{redis_info.get('redis_version')})")
            except Exception as e:
                redis_status = self.style.WARNING(f"Configured but unreachable: {e}")
        else:
            redis_status = self.style.NOTICE("Not configured (using in-process executor / SQLite)")

        self.stdout.write(f"Broker / Redis Status: {redis_status}")

        # 2. Status counts
        qs = IngestionJob.objects.all()
        if wedding:
            qs = qs.filter(wedding=wedding)
            self.stdout.write(f"Scope: Wedding '{wedding.slug}' ({wedding.name})")
        else:
            self.stdout.write("Scope: Global (all weddings)")

        total = qs.count()
        received = qs.filter(status='RECEIVED').count()
        queued = qs.filter(status='QUEUED').count()
        uploading = qs.filter(status='UPLOADING').count()
        cld_done = qs.filter(status='CLOUDINARY_COMPLETED').count()
        db_reg = qs.filter(status='DB_REGISTERED').count()
        face_proc = qs.filter(status='FACE_PROCESSING').count()
        completed = qs.filter(status='COMPLETED').count()
        failed = qs.filter(status='FAILED').count()
        dead_letter = qs.filter(status='DEAD_LETTER').count()

        in_flight = received + queued + uploading + cld_done + db_reg + face_proc
        failure_rate = ((failed + dead_letter) / total * 100) if total > 0 else 0.0

        self.stdout.write("-" * 65)
        self.stdout.write(f"Total Jobs Recorded:    {total}")
        self.stdout.write(f"In-Flight / Active:     {self.style.WARNING(str(in_flight)) if in_flight > 0 else self.style.SUCCESS('0')}")
        self.stdout.write(f"  * RECEIVED:           {received}")
        self.stdout.write(f"  * QUEUED:             {queued}")
        self.stdout.write(f"  * UPLOADING:          {uploading}")
        self.stdout.write(f"  * CLOUDINARY_DONE:    {cld_done}")
        self.stdout.write(f"  * DB_REGISTERED:      {db_reg}")
        self.stdout.write(f"  * FACE_PROCESSING:    {face_proc}")
        self.stdout.write(f"Completed Successfully: {self.style.SUCCESS(str(completed))}")
        self.stdout.write(f"Failed (Retryable):     {self.style.WARNING(str(failed)) if failed > 0 else '0'}")
        self.stdout.write(f"Dead-Letter (Permanent):{self.style.ERROR(str(dead_letter)) if dead_letter > 0 else '0'}")
        self.stdout.write(f"Failure Rate:           {failure_rate:.2f}%")

        # 3. Oldest pending job age
        oldest_pending = qs.filter(
            status__in=['RECEIVED', 'QUEUED', 'UPLOADING', 'DB_REGISTERED', 'FACE_PROCESSING']
        ).order_by('received_at').first()

        if oldest_pending and oldest_pending.received_at:
            age_seconds = (timezone.now() - oldest_pending.received_at).total_seconds()
            if age_seconds > 120:
                age_str = self.style.WARNING(f"{age_seconds / 60:.1f} minutes ago (Job: {oldest_pending.job_id})")
            else:
                age_str = self.style.SUCCESS(f"{age_seconds:.0f} seconds ago (Job: {oldest_pending.job_id})")
            self.stdout.write(f"Oldest Pending Job Age: {age_str}")
        else:
            self.stdout.write(f"Oldest Pending Job Age: {self.style.SUCCESS('None (Queue is idle)')}")

        # 4. Staging storage footprint
        staging_dir = os.path.join(settings.MEDIA_ROOT, 'staging')
        staging_files = 0
        staging_bytes = 0
        if os.path.exists(staging_dir):
            for root, _, files in os.walk(staging_dir):
                for f in files:
                    staging_files += 1
                    try:
                        staging_bytes += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
        staging_mb = staging_bytes / (1024 * 1024)
        self.stdout.write(f"Local Staging Disk:     {staging_files} files ({staging_mb:.2f} MB)")
        self.stdout.write("=" * 65)

    def inspect_dead_letter(self, wedding=None):
        qs = IngestionJob.objects.filter(status='DEAD_LETTER')
        if wedding:
            qs = qs.filter(wedding=wedding)

        total_dead = qs.count()
        self.stdout.write(self.style.NOTICE(f"\n--- Dead-Letter Jobs ({total_dead} total) ---"))
        if total_dead == 0:
            self.stdout.write(self.style.SUCCESS("No dead-letter jobs found."))
            return

        for job in qs.order_by('-failed_at')[:30]:
            self.stdout.write(self.style.ERROR(f"\nJob ID:    {job.job_id}"))
            self.stdout.write(f"Wedding:   {job.wedding.slug}")
            self.stdout.write(f"File:      {job.original_filename} ({job.file_size / (1024*1024):.2f} MB)")
            self.stdout.write(f"Attempts:  {job.attempts}/{job.max_attempts}")
            self.stdout.write(f"Failed At: {job.failed_at}")
            self.stdout.write(f"Reason:    {self.style.WARNING(str(job.dead_letter_reason))}")
            if job.last_error:
                self.stdout.write(f"Error:     {job.last_error}")

    def retry_failed_jobs(self, wedding=None):
        qs = IngestionJob.objects.filter(status='FAILED')
        if wedding:
            qs = qs.filter(wedding=wedding)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No FAILED jobs to retry."))
            return

        retried = 0
        skipped = 0
        for job in qs:
            if not job.cloudinary_public_id and (not job.staging_path or not os.path.exists(job.staging_path)):
                skipped += 1
                continue

            job.status = 'QUEUED'
            job.next_retry_at = timezone.now()
            job.save(update_fields=['status', 'next_retry_at', 'updated_at'])
            enqueue_job(job)
            retried += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully re-enqueued {retried} failed jobs ({skipped} skipped due to missing local staging files)."))

    def retry_dead_letter_jobs(self, wedding=None):
        qs = IngestionJob.objects.filter(status='DEAD_LETTER')
        if wedding:
            qs = qs.filter(wedding=wedding)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No DEAD_LETTER jobs to retry."))
            return

        retried = 0
        skipped = 0
        for job in qs:
            if not job.cloudinary_public_id and (not job.staging_path or not os.path.exists(job.staging_path)):
                skipped += 1
                continue

            job.status = 'QUEUED'
            job.attempts = 0
            job.last_error = None
            job.dead_letter_reason = None
            job.queued_at = timezone.now()
            job.save(update_fields=['status', 'attempts', 'last_error', 'dead_letter_reason', 'queued_at', 'updated_at'])
            enqueue_job(job)
            retried += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully reset and re-enqueued {retried} dead-letter jobs ({skipped} skipped due to missing local files)."))

    def retry_specific_job(self, job_id_str):
        try:
            job_id = uuid.UUID(job_id_str)
        except ValueError:
            self.stderr.write(self.style.ERROR(f"Invalid UUID: '{job_id_str}'"))
            return

        job = IngestionJob.objects.filter(job_id=job_id).first()
        if not job:
            self.stderr.write(self.style.ERROR(f"IngestionJob {job_id} not found."))
            return

        if not job.cloudinary_public_id and (not job.staging_path or not os.path.exists(job.staging_path)):
            self.stderr.write(self.style.ERROR(f"Cannot retry job {job_id}: Staging file missing on disk and Cloudinary upload not completed."))
            return

        job.status = 'QUEUED'
        job.attempts = 0
        job.last_error = None
        job.dead_letter_reason = None
        job.queued_at = timezone.now()
        job.save()
        enqueue_job(job)
        self.stdout.write(self.style.SUCCESS(f"Job {job.job_id} ({job.original_filename}) reset and re-enqueued successfully."))

    def purge_dead_letter_jobs(self, older_than_days, wedding=None):
        cutoff = timezone.now() - timedelta(days=older_than_days)
        qs = IngestionJob.objects.filter(status='DEAD_LETTER', received_at__lt=cutoff)
        if wedding:
            qs = qs.filter(wedding=wedding)

        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS(f"No DEAD_LETTER jobs older than {older_than_days} days to purge."))
            return

        deleted_count, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Purged {deleted_count} DEAD_LETTER jobs older than {older_than_days} days."))

