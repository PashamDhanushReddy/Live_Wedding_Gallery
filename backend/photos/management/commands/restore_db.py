"""
Database Restore Management Command for Live Wedding Gallery.
Restores application metadata from verified, compressed backup snapshots:
- Validates SHA-256 archive integrity
- Supports dry-run inspection and validation
- Restores atomically with post-restoration verification
"""

import os
import io
import gzip
import json
import hashlib
from typing import Dict, Any, Tuple
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
from django.apps import apps


class Command(BaseCommand):
    help = "Restores NeonDB application metadata from a compressed or raw backup archive."

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup-file',
            type=str,
            required=True,
            help='Path to the backup archive (.json or .json.gz).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Inspect and validate the backup archive without writing to the database.',
        )
        parser.add_argument(
            '--skip-checksum',
            action='store_true',
            help='Skip sidecar .sha256 verification.',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm execution when performing actual restoration.',
        )

    def handle(self, *args, **options):
        backup_file = options['backup_file']
        dry_run = options['dry_run']
        skip_checksum = options['skip_checksum']
        confirm = options['confirm']

        if not os.path.exists(backup_file):
            self.stderr.write(self.style.ERROR(f"Backup file not found at: {backup_file}"))
            return

        self.stdout.write(self.style.NOTICE(f"=== Starting Database Restoration ({backup_file}) ==="))

        # 1. Verify SHA-256 Checksum if .sha256 sidecar exists
        checksum_file = f"{backup_file}.sha256"
        if not skip_checksum and os.path.exists(checksum_file):
            self.stdout.write("Verifying archive SHA-256 integrity...")
            with open(checksum_file, 'r', encoding='utf-8') as f_sha:
                expected_sha = f_sha.read().split()[0].strip()

            hasher = hashlib.sha256()
            with open(backup_file, 'rb') as f_in:
                while chunk := f_in.read(65536):
                    hasher.update(chunk)
            actual_sha = hasher.hexdigest()

            if expected_sha.lower() != actual_sha.lower():
                self.stderr.write(self.style.ERROR(
                    f"Integrity check FAILED!\nExpected: {expected_sha}\nActual:   {actual_sha}"
                ))
                return
            self.stdout.write(self.style.SUCCESS("[OK] Archive integrity verified (SHA-256 match)."))

        # 2. Decompress & Parse Snapshot Payload
        manifest, raw_fixture_json = self.load_backup_payload(backup_file)

        self.stdout.write(self.style.NOTICE("--- Backup Archive Manifest ---"))
        self.stdout.write(f"  Created At: {manifest.get('created_at', 'unknown')}")
        self.stdout.write(f"  Tag:        {manifest.get('tag', 'unknown')}")
        self.stdout.write(f"  Scope:      {manifest.get('wedding_scope', 'ALL')}")
        self.stdout.write(f"  Records:    {manifest.get('total_records', len(raw_fixture_json))}")
        for model_name, cnt in manifest.get('table_record_counts', {}).items():
            self.stdout.write(f"  - {model_name}: {cnt} rows")

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                "[OK] DRY-RUN complete: Archive is valid, readable, and ready for restoration."
            ))
            return

        if not confirm:
            self.stderr.write(self.style.WARNING(
                "Action requires confirmation! Please pass '--confirm' to proceed with actual restoration."
            ))
            return

        # 3. Perform Transactional Restoration
        temp_fixture_path = f"{backup_file}.temp_restore.json"
        try:
            with open(temp_fixture_path, 'w', encoding='utf-8') as f_tmp:
                json.dump(raw_fixture_json, f_tmp, indent=2)

            with transaction.atomic():
                self.stdout.write("Loading objects via Django deserializer...")
                call_command('loaddata', temp_fixture_path, verbosity=1)

            self.stdout.write(self.style.SUCCESS("[OK] Restoration committed successfully."))

            # 4. Verify Post-Restoration Counts
            self.stdout.write(self.style.NOTICE("--- Post-Restoration Verification ---"))
            for model_name, expected_count in manifest.get('table_record_counts', {}).items():
                try:
                    m_cls = apps.get_model(model_name)
                    actual_count = m_cls.objects.count()
                    status_style = self.style.SUCCESS if actual_count >= expected_count else self.style.WARNING
                    self.stdout.write(status_style(f"  - {model_name}: {actual_count} rows in DB (Manifest: {expected_count})"))
                except Exception as e:
                    self.stderr.write(f"  - {model_name}: Error verifying count: {e}")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Restoration failed! Transaction rolled back: {e}"))
            raise
        finally:
            if os.path.exists(temp_fixture_path):
                try:
                    os.remove(temp_fixture_path)
                except OSError:
                    pass

    def load_backup_payload(self, file_path: str) -> Tuple[Dict[str, Any], Any]:
        """Loads and extracts manifest and fixture data from gzip or json file."""
        if file_path.endswith('.gz'):
            with gzip.open(file_path, 'rt', encoding='utf-8') as f_in:
                parsed = json.load(f_in)
        else:
            with open(file_path, 'r', encoding='utf-8') as f_in:
                parsed = json.load(f_in)

        # Check if structured manifest container or plain dumpdata array
        if isinstance(parsed, dict) and 'metadata' in parsed and 'data' in parsed:
            return parsed['metadata'], parsed['data']
        elif isinstance(parsed, list):
            # Legacy or standard dumpdata array
            return {'total_records': len(parsed)}, parsed
        else:
            raise ValueError("Unrecognized backup format: Root element must be a list or dict with 'data'.")
