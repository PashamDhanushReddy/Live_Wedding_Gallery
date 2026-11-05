import sys
import time
from django.core.management.base import BaseCommand
from photos.models import Photo
from weddings.models import Wedding
from faces.face_service import generate_embeddings_for_photo


class Command(BaseCommand):
    help = "Batch processes face embeddings and categorization for historical wedding photos."

    def add_arguments(self, parser):
        parser.add_argument(
            '--wedding',
            type=str,
            help='Filter photos by wedding slug.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of photos to process per batch (default: 50).',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Maximum number of photos to process.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-generation of embeddings even for photos that already have face records.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Count photos requiring processing without executing face extraction.',
        )
        parser.add_argument(
            '--async',
            action='store_true',
            dest='async_mode',
            help='Dispatch chunks to Celery background worker queue (batch_indexing) instead of processing in foreground CLI.',
        )

    def handle(self, *args, **options):
        wedding_slug = options.get('wedding')
        batch_size = options.get('batch_size') or 50
        limit = options.get('limit')
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)
        async_mode = options.get('async_mode', False)

        qs = Photo.objects.all().order_by('-created_at')

        if wedding_slug:
            wedding = Wedding.objects.filter(slug=wedding_slug).first()
            if not wedding:
                self.stderr.write(self.style.ERROR(f"Wedding with slug '{wedding_slug}' not found."))
                return
            qs = qs.filter(wedding=wedding)

        if not force:
            # Only select photos without face records
            qs = qs.filter(faces__isnull=True)

        total_photos = qs.count()
        if limit:
            total_photos = min(total_photos, limit)

        self.stdout.write(self.style.NOTICE(
            f"=== Batch Face Embedding Processor ===\n"
            f"Target Photos: {total_photos}\n"
            f"Batch Size:    {batch_size}\n"
            f"Force Mode:    {force}\n"
            f"Dry Run:       {dry_run}\n"
            f"Async Mode:    {async_mode}\n"
        ))

        if total_photos == 0:
            self.stdout.write(self.style.SUCCESS("All photos already have face embeddings generated. Nothing to do!"))
            return

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run complete. {total_photos} photos would be processed."))
            return

        # Use an iterator over photo IDs to avoid loading all objects into RAM
        target_qs = qs[:limit] if limit else qs
        id_iterator = target_qs.values_list('id', flat=True).iterator(chunk_size=batch_size)

        if async_mode:
            from faces.tasks import process_batch_embeddings_task
            dispatched_batches = 0
            dispatched_photos = 0
            current_batch = []

            for photo_id in id_iterator:
                current_batch.append(photo_id)
                if len(current_batch) >= batch_size:
                    process_batch_embeddings_task.apply_async(
                        args=[current_batch, force],
                        queue='batch_indexing',
                        priority=1
                    )
                    dispatched_batches += 1
                    dispatched_photos += len(current_batch)
                    current_batch = []

            if current_batch:
                process_batch_embeddings_task.apply_async(
                    args=[current_batch, force],
                    queue='batch_indexing',
                    priority=1
                )
                dispatched_batches += 1
                dispatched_photos += len(current_batch)

            self.stdout.write(self.style.SUCCESS(
                f"Dispatched {dispatched_batches} batch tasks ({dispatched_photos} photos) "
                f"to Celery 'batch_indexing' queue (priority=1)."
            ))
            return

        # Synchronous execution: process one by one in foreground
        start_time = time.time()
        processed_count = 0
        total_faces_created = 0
        failed_count = 0

        for i, photo_id in enumerate(id_iterator):
            photo = Photo.objects.filter(id=photo_id).first()
            if not photo:
                continue

            sys.stdout.write(f"\r[{i+1}/{total_photos}] Processing Photo {photo.id} ({photo.original_filename})... ")
            sys.stdout.flush()

            try:
                faces = generate_embeddings_for_photo(photo=photo, force=force)
                total_faces_created += len(faces)
                processed_count += 1
            except Exception as e:
                failed_count += 1
                self.stdout.write(self.style.WARNING(f"\nFailed on photo {photo.id}: {e}"))

        elapsed = time.time() - start_time
        speed = processed_count / elapsed if elapsed > 0 else 0

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(
            f"Batch Face Processing Completed in {elapsed:.1f}s!\n"
            f"  Photos processed: {processed_count}\n"
            f"  Faces registered: {total_faces_created}\n"
            f"  Failed photos:    {failed_count}\n"
            f"  Throughput:       {speed:.2f} photos/sec"
        ))
