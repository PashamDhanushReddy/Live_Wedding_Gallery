"""
Automated Unit and Integration Tests for Backup, Restore, and Cloudinary Reconciliation.
Tests:
- Logical database snapshot generation and gzip compression
- SHA-256 integrity checksum generation and verification
- Checksum mismatch / tampering detection
- Dry-run restoration and manifest validation
- Cloudinary vs NeonDB asset reconciliation and orphan restoration
- Staging restoration drill execution
"""

import os
import gzip
import json
import tempfile
import hashlib
from unittest.mock import patch, MagicMock

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import SimpleTestCase
from django.core.management import call_command
from django.utils import timezone

from weddings.models import Wedding
from photos.models import Photo


class BackupManagementCommandTests(SimpleTestCase):
    """Tests the backup_db command logic and output formatting."""

    def test_backup_creates_compressed_archive_and_checksum(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('django.core.management.commands.dumpdata.Command.handle') as mock_dump:
                mock_dump.return_value = json.dumps([
                    {
                        "model": "weddings.wedding",
                        "pk": 1,
                        "fields": {
                            "slug": "test-slug",
                            "wedding_title": "Test Wedding",
                            "bride_name": "Alice",
                            "groom_name": "Bob",
                            "wedding_date": "2026-11-21",
                            "is_active": True
                        }
                    }
                ])

                call_command('backup_db', '--output-dir', temp_dir, '--tag', 'unit-test')

                # Verify files created
                files = os.listdir(temp_dir)
                gz_files = [f for f in files if f.endswith('.json.gz')]
                sha_files = [f for f in files if f.endswith('.sha256')]

                self.assertEqual(len(gz_files), 1)
                self.assertEqual(len(sha_files), 1)

                backup_file = os.path.join(temp_dir, gz_files[0])
                sha_file = os.path.join(temp_dir, sha_files[0])

                # Verify checksum matches actual file
                hasher = hashlib.sha256()
                with open(backup_file, 'rb') as f:
                    hasher.update(f.read())
                actual_sha = hasher.hexdigest()

                with open(sha_file, 'r', encoding='utf-8') as f:
                    recorded_sha = f.read().split()[0].strip()

                self.assertEqual(actual_sha, recorded_sha)

                # Verify manifest
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f_in:
                    payload = json.load(f_in)
                    self.assertIn('metadata', payload)
                    self.assertIn('data', payload)
                    self.assertEqual(payload['metadata']['tag'], 'unit-test')

    def test_backup_uncompressed_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('django.core.management.commands.dumpdata.Command.handle') as mock_dump:
                mock_dump.return_value = json.dumps([])

                call_command('backup_db', '--output-dir', temp_dir, '--no-compress', '--tag', 'raw-test')

                files = os.listdir(temp_dir)
                json_files = [f for f in files if f.endswith('.json') and not f.endswith('.gz')]
                self.assertEqual(len(json_files), 1)


class RestoreManagementCommandTests(SimpleTestCase):
    """Tests the restore_db command and integrity verification."""

    def test_restore_verifies_checksum_and_dry_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = os.path.join(temp_dir, "test_backup.json")
            sha_path = f"{backup_path}.sha256"

            data = {
                'metadata': {
                    'created_at': '2026-11-05T00:00:00Z',
                    'tag': 'dry-run-test',
                    'total_records': 1,
                    'table_record_counts': {'photos.Photo': 1}
                },
                'data': [
                    {'model': 'photos.photo', 'pk': 1, 'fields': {'original_filename': 'img.jpg'}}
                ]
            }

            content = json.dumps(data).encode('utf-8')
            with open(backup_path, 'wb') as f:
                f.write(content)

            sha256 = hashlib.sha256(content).hexdigest()
            with open(sha_path, 'w', encoding='utf-8') as f:
                f.write(f"{sha256}  test_backup.json\n")

            # Execute dry-run restoration
            call_command('restore_db', '--backup-file', backup_path, '--dry-run')

    def test_restore_fails_on_checksum_tampering(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = os.path.join(temp_dir, "tampered.json")
            sha_path = f"{backup_path}.sha256"

            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({'data': []}))

            # Write wrong checksum
            with open(sha_path, 'w', encoding='utf-8') as f:
                f.write("0000000000000000000000000000000000000000000000000000000000000000  tampered.json\n")

            # Should abort due to checksum mismatch
            with patch('sys.stderr.write') as mock_err:
                call_command('restore_db', '--backup-file', backup_path, '--dry-run')
                # Verify error message logged
                has_integrity_err = any("Integrity check FAILED" in str(c) for c in mock_err.call_args_list)
                self.assertTrue(has_integrity_err)


class ReconciliationCommandTests(SimpleTestCase):
    """Tests the reconcile_assets command for Cloudinary vs NeonDB discrepancies."""

    @patch('cloudinary.api.resources')
    @patch('weddings.models.Wedding.objects.filter')
    @patch('photos.models.Photo.objects.filter')
    def test_reconciliation_detects_matched_and_orphans(self, mock_photo_filter, mock_wedding_filter, mock_cld_resources):
        wedding = Wedding(id=1, slug="alice-bob", wedding_title="Alice & Bob")
        mock_wedding_filter.return_value.first.return_value = wedding

        photo_existing = Photo(
            id=10,
            wedding=wedding,
            cloudinary_public_id="weddings/alice-bob/Ceremony/2026-11-21/existing_123",
            original_filename="ring.jpg"
        )
        mock_photo_filter.return_value = [photo_existing]

        # Cloudinary returns 1 matching asset and 1 orphaned asset
        mock_cld_resources.return_value = {
            'resources': [
                {
                    'public_id': "weddings/alice-bob/Ceremony/2026-11-21/existing_123",
                    'secure_url': "https://res.cloudinary.com/test/ring.jpg",
                    'bytes': 2048000,
                    'format': 'jpg',
                    'width': 3000,
                    'height': 2000,
                    'created_at': '2026-11-21T10:00:00Z',
                },
                {
                    'public_id': "weddings/alice-bob/Reception/2026-11-21/orphan_456",
                    'secure_url': "https://res.cloudinary.com/test/cake.jpg",
                    'bytes': 3100000,
                    'format': 'jpg',
                    'width': 4000,
                    'height': 3000,
                    'created_at': '2026-11-21T18:00:00Z',
                }
            ],
            'next_cursor': None
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = os.path.join(temp_dir, "reconcile_report.json")
            call_command(
                'reconcile_assets',
                '--wedding', 'alice-bob',
                '--dry-run',
                '--output-json', report_path
            )

            self.assertTrue(os.path.exists(report_path))
            with open(report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)

            self.assertEqual(report['matched_count'], 1)
            self.assertEqual(report['orphans_in_cloudinary_count'], 1)
            self.assertEqual(report['missing_in_cloudinary_count'], 0)


class StagingDrillCommandTests(SimpleTestCase):
    """Tests the staging recovery drill end-to-end command."""

    @patch('photos.management.commands.backup_db.Command.handle')
    @patch('photos.management.commands.restore_db.Command.handle')
    def test_staging_drill_execution(self, mock_restore, mock_backup):
        # Staging drill calls backup_db and restore_db --dry-run
        mock_backup.return_value = "/tmp/test.json.gz"
        mock_restore.return_value = None

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create dummy backup file so test_restore_staging sees it
            dummy_file = os.path.join(temp_dir, "test.json.gz")
            with gzip.open(dummy_file, 'wb') as f:
                f.write(b"{}")

            with patch('tempfile.TemporaryDirectory') as mock_temp:
                mock_temp.return_value.__enter__.return_value = temp_dir
                call_command('test_restore_staging')

                mock_backup.assert_called_once()
                mock_restore.assert_called_once()

