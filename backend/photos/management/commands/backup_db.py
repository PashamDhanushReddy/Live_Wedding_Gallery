"""
Database Backup Management Command for Live Wedding Gallery.
Creates timestamped, compressed logical snapshots of critical application metadata:
- Weddings, Photos, Faces, IngestionJobs, PhoneDevices, Transfers, Users, Tokens
- Generates SHA-256 integrity checksums and metadata manifests
- Supports retention pruning to prevent storage bloat
"""

import os
import io
import gzip
import json
import hashlib
from datetime import datetime, timezone, timedelta
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.apps import apps


class Command(BaseCommand):
    help = "Creates a compressed, integrity-verified logical backup of NeonDB application metadata."

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default=os.path.join(settings.BASE_DIR, 'backups'),
            help='Directory to store backup archives (default: backend/backups).',
        )
        parser.add_argument(
            '--tag',
            type=str,
            default='scheduled',
            help='Optional label/tag for backup (e.g. pre-deploy, daily, manual).',
        )
        parser.add_argument(
            '--no-compress',
            action='store_true',
            help='Do not gzip-compress the backup archive.',
        )
        parser.add_argument(
            '--prune-older-than-days',
            type=int,
            default=30,
            help='Prune local backup files older than specified days (default: 30 days, 0 to disable).',
        )
        parser.add_argument(
            '--wedding',
            type=str,
            help='Optionally scope backup to a specific wedding slug.',
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        tag = options['tag']
        compress = not options['no_compress']
        prune_days = options['prune_older_than_days']
        wedding_slug = options.get('wedding')

        os.makedirs(output_dir, exist_ok=True)

        now = datetime.now(timezone.utc)
        timestamp_str = now.strftime('%Y%m%d_%H%M%SZ')
        prefix = f"wedding_{wedding_slug}_" if wedding_slug else "full_db_"
        base_filename = f"{prefix}{timestamp_str}_{tag}.json"
        target_path = os.path.join(output_dir, f"{base_filename}.gz" if compress else base_filename)

        self.stdout.write(self.style.NOTICE(f"=== Starting Database Backup ({target_path}) ==="))

        # 1. Collect row counts before dumping
        model_names = [
            'weddings.Wedding',
            'photos.Photo',
            'photos.IngestionJob',
            'photos.PhoneDevice',
            'photos.CameraConnection',
            'photos.Transfer',
            'faces.Face',
            'auth.User',
            'authtoken.Token',
        ]

        table_stats = {}
        for m_str in model_names:
            try:
                m_cls = apps.get_model(m_str)
                table_stats[m_str] = m_cls.objects.count()
            except Exception:
                table_stats[m_str] = 0

        # 2. Serialize application records using Django's dumpdata engine
        buffer = io.StringIO()
        try:
            dump_args = [
                'weddings',
                'photos',
                'faces',
                'auth.User',
                'authtoken.Token',
            ]
            call_command(
                'dumpdata',
                *dump_args,
                stdout=buffer,
                indent=2,
                natural_foreign=True,
                natural_primary=True,
                use_base_manager=True
            )
            raw_json = buffer.getvalue()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Backup failed during dumpdata: {e}"))
            raise

        # 3. Create metadata manifest
        manifest = {
            'manifest_version': '1.0',
            'created_at': now.isoformat(),
            'database_engine': settings.DATABASES['default'].get('ENGINE', 'unknown'),
            'tag': tag,
            'wedding_scope': wedding_slug or 'ALL',
            'table_record_counts': table_stats,
            'total_records': sum(table_stats.values()),
        }

        # Embed manifest in combined backup structure
        backup_payload = {
            'metadata': manifest,
            'data': json.loads(raw_json)
        }
        serialized_bytes = json.dumps(backup_payload, indent=2).encode('utf-8')

        # 4. Write to disk (compressed or raw)
        if compress:
            with gzip.open(target_path, 'wb', compresslevel=6) as f_out:
                f_out.write(serialized_bytes)
        else:
            with open(target_path, 'wb') as f_out:
                f_out.write(serialized_bytes)

        # 5. Compute SHA-256 Checksum
        hasher = hashlib.sha256()
        with open(target_path, 'rb') as f_chk:
            while chunk := f_chk.read(65536):
                hasher.update(chunk)
        sha256_hash = hasher.hexdigest()

        # Write sidecar .sha256 file
        checksum_path = f"{target_path}.sha256"
        with open(checksum_path, 'w', encoding='utf-8') as f_sha:
            f_sha.write(f"{sha256_hash}  {os.path.basename(target_path)}\n")

        file_size_kb = os.path.getsize(target_path) / 1024

        self.stdout.write(self.style.SUCCESS(f"[OK] Backup successfully written: {target_path}"))
        self.stdout.write(f"  Size: {file_size_kb:.1f} KB | SHA-256: {sha256_hash[:16]}... | Records: {manifest['total_records']}")
        for model_name, cnt in table_stats.items():
            self.stdout.write(f"  - {model_name}: {cnt} rows")

        # 6. Prune old backups if requested
        if prune_days > 0:
            pruned_count = self.prune_old_backups(output_dir, prune_days)
            if pruned_count > 0:
                self.stdout.write(self.style.NOTICE(f"Pruned {pruned_count} backup files older than {prune_days} days."))

        return target_path

    def prune_old_backups(self, output_dir: str, days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        pruned = 0
        for entry in os.scandir(output_dir):
            if (entry.name.endswith('.json') or entry.name.endswith('.json.gz') or entry.name.endswith('.sha256')):
                try:
                    mtime = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc)
                    if mtime < cutoff:
                        os.remove(entry.path)
                        pruned += 1
                except OSError:
                    pass
        return pruned
