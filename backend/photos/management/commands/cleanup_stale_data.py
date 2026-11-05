import os
import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from photos.models import Transfer, IngestionJob

class Command(BaseCommand):
    help = "Cleans up stale transfers, old completed ingestion jobs, legacy queue rows, and abandoned staging files."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate cleanup without deleting any database records or files.',
        )
        parser.add_argument(
            '--job-retention-days',
            type=int,
            default=7,
            help='Retention period in days for COMPLETED IngestionJob records (default: 7).',
        )
        parser.add_argument(
            '--transfer-retention-days',
            type=int,
            default=3,
            help='Retention period in days for Transfer records (default: 3).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        job_retention = options['job_retention_days']
        transfer_retention = options['transfer_retention_days']

        now = timezone.now()
        job_cutoff = now - timedelta(days=job_retention)
        transfer_cutoff = now - timedelta(days=transfer_retention)
        staging_cutoff = time.time() - (24 * 3600)  # 24 hours ago

        self.stdout.write(self.style.NOTICE(f"--- Database Retention & Cleanup (Dry-run: {dry_run}) ---"))

        # 1. Cleanup completed IngestionJob records older than cutoff
        completed_jobs_qs = IngestionJob.objects.filter(
            status='COMPLETED',
            completed_at__lt=job_cutoff
        )
        completed_jobs_count = completed_jobs_qs.count()
        if dry_run:
            self.stdout.write(f"Would delete {completed_jobs_count} completed IngestionJob records older than {job_retention} days.")
        else:
            deleted_jobs, _ = completed_jobs_qs.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_jobs} completed IngestionJob records older than {job_retention} days."))

        # 2. Cleanup dead-letter or failed jobs older than 14 days
        dead_cutoff = now - timedelta(days=14)
        dead_jobs_qs = IngestionJob.objects.filter(
            status__in=['FAILED', 'DEAD_LETTER'],
            received_at__lt=dead_cutoff
        )
        dead_count = dead_jobs_qs.count()
        if dry_run:
            self.stdout.write(f"Would delete {dead_count} dead/failed IngestionJob records older than 14 days.")
        else:
            deleted_dead, _ = dead_jobs_qs.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_dead} dead/failed IngestionJob records older than 14 days."))

        # 3. Cleanup Transfer records older than cutoff
        transfers_qs = Transfer.objects.filter(started_at__lt=transfer_cutoff)
        transfers_count = transfers_qs.count()
        if dry_run:
            self.stdout.write(f"Would delete {transfers_count} Transfer records older than {transfer_retention} days.")
        else:
            deleted_transfers, _ = transfers_qs.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_transfers} Transfer records older than {transfer_retention} days."))

        # 4. Cleanup orphaned local staging files in staging_uploads/
        staging_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'staging_uploads')
        cleaned_files = 0
        if os.path.exists(staging_dir):
            for root, _, files in os.walk(staging_dir):
                for f in files:
                    fpath = os.path.join(root, f)
                    try:
                        if os.path.getmtime(fpath) < staging_cutoff:
                            if dry_run:
                                self.stdout.write(f"Would remove stale staging file: {fpath}")
                            else:
                                os.remove(fpath)
                            cleaned_files += 1
                    except OSError:
                        pass
        self.stdout.write(self.style.SUCCESS(f"Cleaned {cleaned_files} abandoned staging files older than 24 hours."))

        # 5. Check and prune legacy queue_uploads table if present
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'queue_uploads'
                );
            """)
            table_exists = cursor.fetchone()[0]
            if table_exists:
                cursor.execute("SELECT count(*) FROM queue_uploads WHERE status = 'COMPLETED';")
                legacy_count = cursor.fetchone()[0]
                if dry_run:
                    self.stdout.write(f"Would prune {legacy_count} completed rows from legacy queue_uploads table.")
                else:
                    cursor.execute("DELETE FROM queue_uploads WHERE status = 'COMPLETED';")
                    self.stdout.write(self.style.SUCCESS(f"Pruned {legacy_count} completed rows from legacy queue_uploads table."))

        self.stdout.write(self.style.SUCCESS("Cleanup task completed successfully."))

