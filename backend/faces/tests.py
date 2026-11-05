import os
import unittest
import math
import numpy as np
from unittest.mock import patch, MagicMock

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from weddings.models import Wedding
from photos.models import Photo
from faces.models import Face
from faces.face_service import (
    extract_faces_from_image,
    extract_selfie_faces,
    generate_embeddings_for_photo,
    search_photos_by_selfie
)


def create_normalized_embedding(seed: int = 42) -> list:
    """Helper to generate a reproducible 512-dimensional normalized unit vector."""
    np.random.seed(seed)
    vec = np.random.randn(512).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def create_similar_embedding(base_vec: list, noise_level: float = 0.15, seed: int = 99) -> list:
    """Creates a slightly perturbed vector with known cosine distance ~ (noise_level^2 / 2)."""
    np.random.seed(seed)
    base = np.array(base_vec, dtype=np.float32)
    noise = np.random.randn(512).astype(np.float32)
    noise = noise / np.linalg.norm(noise)
    perturbed = base + (noise_level * noise)
    perturbed = perturbed / np.linalg.norm(perturbed)
    return perturbed.tolist()


class FaceRecognitionVectorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from django.db import connection
            connection.ensure_connection()
        except Exception as e:
            raise unittest.SkipTest(f"Live PostgreSQL/pgvector database not reachable: {e}")
        super().setUpClass()

    def setUp(self):
        self.wedding = Wedding.objects.create(
            slug="test-wedding",
            bride_name="Alice",
            groom_name="Bob",
            wedding_date="2026-11-21"
        )
        self.client = APIClient()

    def test_vector_cosine_math(self):
        """Validates that normalized embeddings satisfy cosine distance properties."""
        vec_a = np.array(create_normalized_embedding(1))
        vec_b = np.array(create_similar_embedding(vec_a.tolist(), noise_level=0.2, seed=2))
        vec_c = np.array(create_normalized_embedding(3)) # Completely different person

        # Cosine distance: 1 - dot(a, b)
        dist_same = 1.0 - float(np.dot(vec_a, vec_b))
        dist_diff = 1.0 - float(np.dot(vec_a, vec_c))

        self.assertLess(dist_same, 0.15, "Similar face distance should be small (< 0.15)")
        self.assertGreater(dist_diff, 0.70, "Different face distance should be large (> 0.70)")

    def test_multi_face_in_single_photo(self):
        """
        Requirement 9: Handle multiple faces in one photograph.
        A group photograph with 3 people should store 3 Face records and match
        when searching for any of the individual guests.
        """
        photo = Photo.objects.create(
            wedding=self.wedding,
            original_filename="group_photo.jpg",
            cloudinary_public_id="group_123",
            processing_status="COMPLETED"
        )

        emb_person_1 = create_normalized_embedding(10)
        emb_person_2 = create_normalized_embedding(20)
        emb_person_3 = create_normalized_embedding(30)

        Face.objects.bulk_create([
            Face(photo=photo, embedding=emb_person_1, x=50, y=50, width=100, height=100, detection_confidence=0.95),
            Face(photo=photo, embedding=emb_person_2, x=200, y=50, width=100, height=100, detection_confidence=0.92),
            Face(photo=photo, embedding=emb_person_3, x=350, y=50, width=100, height=100, detection_confidence=0.89),
        ])

        self.assertEqual(photo.faces.count(), 3)

        # Mock searching for Person 2's selfie
        with patch('faces.face_service.extract_selfie_faces') as mock_extract:
            mock_extract.return_value = ([{
                'embedding': create_similar_embedding(emb_person_2, noise_level=0.1),
                'area': 10000,
                'confidence': 0.98
            }], "OK_SINGLE")

            result = search_photos_by_selfie(
                wedding=self.wedding,
                selfie_bytes=b"dummy_bytes",
                threshold=0.45
            )

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['matches_count'], 1)
            self.assertEqual(result['photos'][0]['id'], photo.id)

    def test_false_match_rejection(self):
        """
        Requirement 17 & 18: Preserve accuracy; ensure false matches are rejected.
        A selfie of an uninvited/different person must NOT match wedding photos.
        """
        photo = Photo.objects.create(
            wedding=self.wedding,
            original_filename="guest_photo.jpg",
            cloudinary_public_id="guest_1",
            processing_status="COMPLETED"
        )
        Face.objects.create(
            photo=photo,
            embedding=create_normalized_embedding(100),
            x=50, y=50, width=100, height=100, detection_confidence=0.95
        )

        # Completely unrelated person (orthogonal embedding)
        stranger_emb = create_normalized_embedding(999)

        with patch('faces.face_service.extract_selfie_faces') as mock_extract:
            mock_extract.return_value = ([{
                'embedding': stranger_emb,
                'area': 10000,
                'confidence': 0.95
            }], "OK_SINGLE")

            result = search_photos_by_selfie(
                wedding=self.wedding,
                selfie_bytes=b"stranger_bytes",
                threshold=0.45
            )

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['matches_count'], 0)
            self.assertEqual(len(result['photos']), 0)

    def test_no_face_in_selfie(self):
        """
        Requirement 10: Handle selfies containing no detectable face.
        Must return a descriptive 400 error response with NO_FACE code.
        """
        with patch('faces.face_service.extract_selfie_faces') as mock_extract:
            mock_extract.return_value = ([], "NO_FACE")

            result = search_photos_by_selfie(
                wedding=self.wedding,
                selfie_bytes=b"blurry_bytes",
                threshold=0.45
            )

            self.assertEqual(result['status'], 'no_face_detected')
            self.assertEqual(result['code'], 'NO_FACE')
            self.assertEqual(result['matches_count'], 0)

    def test_multiple_faces_in_selfie(self):
        """
        Requirement 11: Handle multiple faces in a selfie (e.g. couple selfie).
        Should search for all prominent faces and return photos containing either person.
        """
        emb_person_a = create_normalized_embedding(400)
        emb_person_b = create_normalized_embedding(500)

        # Photo 1 has Person A
        p1 = Photo.objects.create(wedding=self.wedding, original_filename="a.jpg", processing_status="COMPLETED")
        Face.objects.create(photo=p1, embedding=emb_person_a, x=0, y=0, width=10, height=10, detection_confidence=0.9)

        # Photo 2 has Person B
        p2 = Photo.objects.create(wedding=self.wedding, original_filename="b.jpg", processing_status="COMPLETED")
        Face.objects.create(photo=p2, embedding=emb_person_b, x=0, y=0, width=10, height=10, detection_confidence=0.9)

        # Selfie contains both Person A and Person B
        with patch('faces.face_service.extract_selfie_faces') as mock_extract:
            mock_extract.return_value = ([
                {'embedding': emb_person_a, 'area': 12000, 'confidence': 0.95},
                {'embedding': emb_person_b, 'area': 11000, 'confidence': 0.93}
            ], "OK_MULTIPLE")

            result = search_photos_by_selfie(
                wedding=self.wedding,
                selfie_bytes=b"couple_selfie_bytes",
                threshold=0.45
            )

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['matches_count'], 2)
            matched_ids = {p['id'] for p in result['photos']}
            self.assertIn(p1.id, matched_ids)
            self.assertIn(p2.id, matched_ids)
            self.assertEqual(result['selfie_faces_detected'], 2)

    def test_idempotent_embedding_generation(self):
        """
        Requirement 2 & 12: Generate embeddings only once per photo; avoid repeated processing.
        """
        photo = Photo.objects.create(
            wedding=self.wedding,
            original_filename="idempotent_test.jpg",
            processing_status="COMPLETED"
        )
        Face.objects.create(
            photo=photo,
            embedding=create_normalized_embedding(777),
            x=10, y=10, width=50, height=50, detection_confidence=0.9
        )
        self.assertEqual(photo.faces.count(), 1)

        # Second call to generate_embeddings_for_photo without force=True must NOT recreate faces
        faces = generate_embeddings_for_photo(photo=photo, force=False)
        self.assertEqual(len(faces), 1)
        self.assertEqual(photo.faces.count(), 1, "Face count should remain 1 without duplicates")

    def test_pagination_of_search_results(self):
        """
        Requirement 15: Paginate matching results to avoid huge JSON memory payloads.
        """
        emb_target = create_normalized_embedding(888)

        # Create 5 photos matching the same face
        for i in range(5):
            p = Photo.objects.create(wedding=self.wedding, original_filename=f"photo_{i}.jpg", processing_status="COMPLETED")
            Face.objects.create(photo=p, embedding=emb_target, x=0, y=0, width=10, height=10, detection_confidence=0.9)

        with patch('faces.face_service.extract_selfie_faces') as mock_extract:
            mock_extract.return_value = ([{'embedding': emb_target, 'area': 10000, 'confidence': 0.95}], "OK_SINGLE")

            # Request page 1 with page_size=2
            result_p1 = search_photos_by_selfie(
                wedding=self.wedding,
                selfie_bytes=b"selfie",
                threshold=0.45,
                page=1,
                page_size=2
            )

            self.assertEqual(result_p1['matches_count'], 5)
            self.assertEqual(len(result_p1['photos']), 2)
            self.assertEqual(result_p1['total_pages'], 3)
            self.assertEqual(result_p1['page'], 1)

            # Request page 2 with page_size=2
            result_p2 = search_photos_by_selfie(
                wedding=self.wedding,
                selfie_bytes=b"selfie",
                threshold=0.45,
                page=2,
                page_size=2
            )
            self.assertEqual(len(result_p2['photos']), 2)
            self.assertEqual(result_p2['page'], 2)

    def test_configurable_threshold(self):
        """
        Requirement 8: Implement configurable similarity thresholds.
        """
        base_emb = np.array(create_normalized_embedding(300), dtype=np.float32)
        ortho_emb = np.array(create_normalized_embedding(700), dtype=np.float32)
        # Gram-Schmidt to make ortho strictly perpendicular to base
        ortho_emb = ortho_emb - np.dot(ortho_emb, base_emb) * base_emb
        ortho_emb = ortho_emb / np.linalg.norm(ortho_emb)

        # Construct vector with exact cosine distance 0.40 (cos = 0.60, dist = 0.40)
        border_emb = (0.60 * base_emb + 0.80 * ortho_emb).tolist()

        p = Photo.objects.create(wedding=self.wedding, original_filename="border.jpg", processing_status="COMPLETED")
        Face.objects.create(photo=p, embedding=border_emb, x=0, y=0, width=10, height=10, detection_confidence=0.9)

        with patch('faces.face_service.extract_selfie_faces') as mock_extract:
            mock_extract.return_value = ([{'embedding': base_emb.tolist(), 'area': 10000, 'confidence': 0.95}], "OK_SINGLE")

            # Strict threshold (0.30): rejects the border match (dist 0.40 > 0.30)
            strict_res = search_photos_by_selfie(self.wedding, b"selfie", threshold=0.30)
            self.assertEqual(strict_res['matches_count'], 0)

            # Permissive threshold (0.55): accepts the border match (dist 0.40 < 0.55)
            permissive_res = search_photos_by_selfie(self.wedding, b"selfie", threshold=0.55)
            self.assertEqual(permissive_res['matches_count'], 1)
