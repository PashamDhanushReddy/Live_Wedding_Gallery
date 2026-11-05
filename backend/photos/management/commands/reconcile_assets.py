"""
Cloudinary Asset and NeonDB Record Reconciliation Command.
Reconciles CDN assets with NeonDB metadata:
- Discovers orphaned Cloudinary images (present in CDN but missing in NeonDB)
- Discovers missing Cloudinary assets (present in NeonDB but 404 in CDN)
- Recreates missing database records from Cloudinary asset metadata
- Ensures original images in Cloudinary are never deleted or corrupted
"""

import os
import json
import logging
from typing import Dict, Any, List
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from photos.models import Photo, IngestionJob
from weddings.models import Wedding
from photos.cloudinary_service import (
    configure_cloudinary,
    get_thumbnail_url,
    get_large_preview_url,
    get_download_url
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reconciles Cloudinary CDN assets with NeonDB Photo records, detecting orphans and missing files."

    def add_arguments(self, parser):
        parser.add_argument(
            '--wedding',
            type=str,
            required=True,
            help='Wedding slug to reconcile (e.g. sandeep-prathyusha).',
        )
        parser.add_argument(
            '--auto-restore-orphans',
            action='store_true',
            help='Automatically recreate missing NeonDB Photo records from Cloudinary asset metadata.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate reconciliation and print report without making database changes.',
        )
        parser.add_argument(
            '--output-json',
            type=str,
            help='Optional file path to output structured JSON reconciliation report.',
        )

    def handle(self, *args, **options):
        wedding_slug = options['wedding']
        auto_restore = options['auto_restore_orphans']
        dry_run = options['dry_run']
        output_json = options.get('output_json')

        wedding = Wedding.objects.filter(slug=wedding_slug).first()
        if not wedding:
            self.stderr.write(self.style.ERROR(f"Wedding with slug '{wedding_slug}' not found."))
            return

        self.stdout.write(self.style.NOTICE(f"=== Reconciling Cloudinary Assets vs NeonDB for '{wedding_slug}' ==="))

        if not configure_cloudinary():
            self.stderr.write(self.style.ERROR("Cloudinary is not configured. Check environment credentials."))
            return

        import cloudinary.api

        # 1. Fetch Cloudinary assets under weddings/{wedding_slug}
        prefix = f"weddings/{wedding_slug}"
        self.stdout.write(f"Scanning Cloudinary assets with prefix '{prefix}'...")

        cloudinary_assets: Dict[str, Dict[str, Any]] = {}
        next_cursor = None

        try:
            while True:
                kwargs = {
                    'type': 'upload',
                    'prefix': prefix,
                    'max_results': 500,
                }
                if next_cursor:
                    kwargs['next_cursor'] = next_cursor

                res = cloudinary.api.resources(**kwargs)
                resources = res.get('resources', [])
                for r in resources:
                    pub_id = r.get('public_id')
                    if pub_id:
                        cloudinary_assets[pub_id] = r

                next_cursor = res.get('next_cursor')
                if not next_cursor:
                    break
        except Exception as e:
            self.stderr.write(self.style.WARNING(f"Note on Cloudinary scan: {e}"))
            # In mock or offline mode, fall back to registered Photo IDs for test simulation
            if getattr(settings, 'MOCK_CLOUDINARY', False):
                self.stdout.write(self.style.NOTICE("[MOCK_CLOUDINARY] Running in offline mock mode."))

        # 2. Fetch NeonDB Photo records
        photos = Photo.objects.filter(wedding=wedding)
        neondb_photos_by_pub_id: Dict[str, Photo] = {}
        for p in photos:
            if p.cloudinary_public_id:
                neondb_photos_by_pub_id[p.cloudinary_public_id] = p

        matched = []
        orphans_in_cloudinary = []
        missing_in_cloudinary = []

        # Find matches and orphans
        for pub_id, cld_meta in cloudinary_assets.items():
            if pub_id in neondb_photos_by_pub_id:
                matched.append({
                    'public_id': pub_id,
                    'photo_id': neondb_photos_by_pub_id[pub_id].id,
                })
            else:
                orphans_in_cloudinary.append({
                    'public_id': pub_id,
                    'secure_url': cld_meta.get('secure_url'),
                    'bytes': cld_meta.get('bytes', 0),
                    'format': cld_meta.get('format', 'jpg'),
                    'width': cld_meta.get('width'),
                    'height': cld_meta.get('height'),
                    'created_at': cld_meta.get('created_at'),
                })

        # Find photos in NeonDB that don't exist in Cloudinary
        for pub_id, photo in neondb_photos_by_pub_id.items():
            if pub_id not in cloudinary_assets and not getattr(settings, 'MOCK_CLOUDINARY', False):
                missing_in_cloudinary.append({
                    'photo_id': photo.id,
                    'public_id': pub_id,
                    'filename': photo.original_filename,
                })

        self.stdout.write(self.style.SUCCESS(f"[OK] Matched Assets:              {len(matched)}"))
        self.stdout.write(self.style.WARNING(f"[!] Orphans in Cloudinary (No DB): {len(orphans_in_cloudinary)}"))
        self.stdout.write(self.style.ERROR(f"[X] Missing in Cloudinary (In DB):  {len(missing_in_cloudinary)}"))

        # 3. Auto-restore orphans if requested
        restored_count = 0
        if auto_restore and orphans_in_cloudinary:
            self.stdout.write(self.style.NOTICE(f"\n--- Restoring {len(orphans_in_cloudinary)} Orphaned Records to NeonDB ---"))
            for orphan in orphans_in_cloudinary:
                pub_id = orphan['public_id']
                # Infer folder from public ID: weddings/<slug>/<folder>/...
                parts = pub_id.split('/')
                inferred_folder = parts[2] if len(parts) >= 3 else 'Uncategorized'
                checksum = parts[-1] if len(parts) >= 4 else pub_id.split('_')[-1]
                filename = f"restored_{pub_id.split('/')[-1]}.{orphan['format']}"

                if dry_run:
                    self.stdout.write(f"Would restore Photo from {pub_id} (Folder: {inferred_folder})")
                else:
                    new_photo = Photo.objects.create(
                        wedding=wedding,
                        original_filename=filename,
                        cloudinary_public_id=pub_id,
                        secure_url=orphan['secure_url'],
                        cloudinary_url=orphan['secure_url'],
                        thumbnail_url=get_thumbnail_url(pub_id, orphan['format']),
                        width=orphan['width'],
                        height=orphan['height'],
                        file_size=orphan['bytes'],
                        format=orphan['format'],
                        folder=inferred_folder,
                        checksum=checksum,
                        processing_status='COMPLETED',
                        upload_status='COMPLETED',
                        captured_at=timezone.now(),
                    )
                    restored_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Restored Photo #{new_photo.id}: {pub_id}"))

                    # Trigger face extraction in background
                    try:
                        from faces.face_service import generate_embeddings_for_photo
                        generate_embeddings_for_photo(photo=new_photo, force=False)
                    except Exception as fe:
                        logger.warning(f"Face extraction post-restore for photo {new_photo.id}: {fe}")

            if not dry_run:
                self.stdout.write(self.style.SUCCESS(f"[OK] Successfully restored {restored_count} photos to NeonDB."))

        # 4. Generate structured JSON report if output path provided
        report = {
            'timestamp': timezone.now().isoformat(),
            'wedding_slug': wedding_slug,
            'total_cloudinary_assets': len(cloudinary_assets),
            'total_neondb_photos': len(neondb_photos_by_pub_id),
            'matched_count': len(matched),
            'orphans_in_cloudinary_count': len(orphans_in_cloudinary),
            'missing_in_cloudinary_count': len(missing_in_cloudinary),
            'restored_count': restored_count,
            'orphans': orphans_in_cloudinary[:50],
            'missing': missing_in_cloudinary[:50],
        }

        if output_json:
            with open(output_json, 'w', encoding='utf-8') as f_out:
                json.dump(report, f_out, indent=2)
            self.stdout.write(self.style.SUCCESS(f"Audit report saved to: {output_json}"))

        return None
