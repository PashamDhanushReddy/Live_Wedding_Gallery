import threading
from django.db import models
from django.core.cache import cache
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import CursorPagination
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
import logging

from .models import Wedding
from .serializers import WeddingSerializer
from photos.models import Photo
from photos.serializers import PhotoSerializer, GalleryPhotoSerializer
from photos.security import audit_log, validate_image_file_bytes

logger = logging.getLogger(__name__)

# Concurrency gate to prevent simultaneous face inference from exhausting web CPU
_face_search_semaphore = threading.BoundedSemaphore(value=2)

class GalleryCursorPagination(CursorPagination):
    """
    Cursor-based pagination for high-volume wedding photos:
    - Default: 25 photos per page.
    - Max: 50 photos per page.
    - Ordering: ('-created_at', '-id') ensures absolute determinism and consistency.
    - Prevents duplicate photos or missed items during live real-time photographer uploads.
    - Constant O(1) database response time using composite B-tree indexes.
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 50
    ordering = ('-created_at', '-id')
    cursor_query_param = 'cursor'

    def get_paginated_response(self, data):
        total_count = getattr(self, 'total_count', None)
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'page_size': self.page_size,
            'count': total_count,
            'results': data
        })

class WeddingListCreateView(generics.ListCreateAPIView):
    serializer_class = WeddingSerializer

    def get_queryset(self):
        if self.request.user and self.request.user.is_staff:
            return Wedding.objects.all().order_by('-created_at')
        return Wedding.objects.filter(is_active=True).order_by('-created_at')

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class PhotographerLoginView(APIView):
    throttle_scope = 'photographer_login'

    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        if user and user.is_active:
            token, _ = Token.objects.get_or_create(user=user)
            audit_log('LOGIN_SUCCESS', request=request, user=user, wedding_slug=slug, details=f"user={username}")
            return Response({'status': 'success', 'token': token.key})

        audit_log('LOGIN_FAILED', request=request, wedding_slug=slug, details=f"user={username}", level='warning')
        return Response({'status': 'error', 'message': 'Invalid credentials'}, status=401)

class WeddingDetailView(generics.RetrieveAPIView):
    queryset = Wedding.objects.filter(is_active=True)
    serializer_class = WeddingSerializer
    lookup_field = 'slug'

    def retrieve(self, request, *args, **kwargs):
        slug = self.kwargs.get('slug')
        cache_key = f"wedding_detail:{slug}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            resp = Response(cached_data)
            resp['Cache-Control'] = 'public, max-age=60, stale-while-revalidate=120'
            resp['X-Cache'] = 'HIT'
            return resp

        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=60)
        response['Cache-Control'] = 'public, max-age=60, stale-while-revalidate=120'
        response['X-Cache'] = 'MISS'
        return response

class WeddingPhotosView(generics.ListAPIView):
    """
    Primary gallery listing endpoint with cursor-based pagination and multi-dimensional filters.
    Returns lightweight metadata with Cloudinary responsive thumbnail/preview URLs.
    Never exposes raw uncompressed master asset URLs.
    """
    serializer_class = GalleryPhotoSerializer
    pagination_class = GalleryCursorPagination

    def get_queryset(self):
        slug = self.kwargs.get('slug')
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        
        # Base query: completed photos for this wedding
        qs = Photo.objects.filter(wedding=wedding).filter(
            models.Q(processing_status='COMPLETED') | models.Q(upload_status='COMPLETED')
        )
        
        # 1. Folder / Category filter (resilient to spaces, underscores, and casing)
        folder = self.request.query_params.get('folder')
        if folder and folder.lower() != 'all':
            f_norm = folder.strip()
            f_space = f_norm.replace('_', ' ')
            f_under = f_norm.replace(' ', '_')
            if f_norm.lower() in ['bride', 'groom', 'bride and groom']:
                # Person filter: match photos assigned to this AI face tag or explicit folder
                qs = qs.filter(
                    models.Q(folder__iexact=f_norm) |
                    models.Q(folder__iexact=f_space) |
                    models.Q(folder__iexact=f_under) |
                    models.Q(ai_category__iexact=f_norm) |
                    models.Q(ai_category__iexact=f_space) |
                    models.Q(ai_category__iexact=f_under)
                )
            else:
                # Event folder filter: matches photos uploaded to this event folder (Haldi, Wedding Day, etc.)
                qs = qs.filter(
                    models.Q(folder__iexact=f_norm) |
                    models.Q(folder__iexact=f_space) |
                    models.Q(folder__iexact=f_under)
                )
            
        # 2. Exact date filter (YYYY-MM-DD) or date range
        date_param = self.request.query_params.get('date')
        if date_param:
            qs = qs.filter(created_at__date=date_param)
            
        start_date = self.request.query_params.get('start_date')
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
            
        end_date = self.request.query_params.get('end_date')
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)
            
        # 3. Photographer / Companion Device filter
        device_id = self.request.query_params.get('device_id')
        if device_id:
            qs = qs.filter(ingestion_jobs__device__device_id=device_id).distinct()
            
        photographer = self.request.query_params.get('photographer')
        if photographer:
            qs = qs.filter(
                models.Q(transfers__camera__username__icontains=photographer) |
                models.Q(ingestion_jobs__device__device_id__icontains=photographer)
            ).distinct()
            
        # 4. Search query (original filename)
        search_query = self.request.query_params.get('q') or self.request.query_params.get('search')
        if search_query:
            qs = qs.filter(original_filename__icontains=search_query)

        return qs.order_by('-created_at', '-id')

    def list(self, request, *args, **kwargs):
        slug = self.kwargs.get('slug')
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)

        # Privacy Enforcement: Only authenticated photographers, staff, or registered devices can list all wedding photos
        from photos.views import authenticate_photographer_or_device
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding, allow_device=True)
        if not is_auth:
            return Response({
                'status': 'forbidden',
                'code': 'GALLERY_PRIVACY_RESTRICTED',
                'message': 'Browsing all wedding photos is restricted to the photographer portal to protect attendee privacy. Please scan your face to view your personal photos, or sign in as a photographer.'
            }, status=status.HTTP_403_FORBIDDEN)

        is_first_page = (
            not request.query_params.get('cursor') and
            not request.query_params.get('date') and
            not request.query_params.get('start_date') and
            not request.query_params.get('end_date') and
            not request.query_params.get('photographer') and
            not request.query_params.get('device_id') and
            not request.query_params.get('q') and
            not request.query_params.get('search')
        )
        page_size = request.query_params.get('page_size', 25)
        folder = request.query_params.get('folder', 'all')
        folder_clean = str(folder or 'all').replace(' ', '_')
        first_page_cache_key = f"gallery_p1:{wedding.id}:{folder_clean}:{page_size}"

        if is_first_page:
            cached_page = cache.get(first_page_cache_key)
            if cached_page is not None:
                resp = Response(cached_page)
                resp['Cache-Control'] = 'public, max-age=15, stale-while-revalidate=45'
                resp['X-Cache'] = 'HIT'
                return resp

        queryset = self.filter_queryset(self.get_queryset())
        
        paginator = self.paginator
        if paginator:
            # Cache count query on initial request to prevent connection pool storms
            if not request.query_params.get('cursor'):
                count_cache_key = f"wedding_photo_count:{wedding.id}:{folder_clean}"
                cached_count = cache.get(count_cache_key)
                if cached_count is not None:
                    paginator.total_count = cached_count
                else:
                    paginator.total_count = queryset.count()
                    cache.set(count_cache_key, paginator.total_count, timeout=30)

            page = paginator.paginate_queryset(queryset, request, view=self)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response = paginator.get_paginated_response(serializer.data)
                response['Cache-Control'] = 'public, max-age=15, stale-while-revalidate=45'
                response['X-Cache'] = 'MISS'
                if is_first_page:
                    cache.set(first_page_cache_key, response.data, timeout=15)
                return response
                
        serializer = self.get_serializer(queryset, many=True)
        response = Response(serializer.data)
        response['Cache-Control'] = 'public, max-age=15, stale-while-revalidate=45'
        response['X-Cache'] = 'MISS'
        return response

class PhotoSyncView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        from photos.views import authenticate_photographer_or_device
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err or 'Unauthorized'}, status=401)

        data = request.data
        
        from photos.models import Photo
        from faces.models import Face
        from django.db import transaction
        
        try:
            with transaction.atomic():
                photo, created = Photo.objects.get_or_create(
                    wedding=wedding,
                    checksum=data.get('checksum'),
                    defaults={
                        'original_filename': data.get('original_filename'),
                        'cloudinary_public_id': data.get('cloudinary_public_id'),
                        'cloudinary_url': data.get('cloudinary_url', ''),
                        'secure_url': data.get('secure_url', ''),
                        'thumbnail_url': data.get('thumbnail_url', ''),
                        'width': data.get('width'),
                        'height': data.get('height'),
                        'file_size': data.get('file_size'),
                        'format': data.get('format', ''),
                        'resource_type': data.get('resource_type', 'image'),
                        'processing_status': 'COMPLETED'
                    }
                )
                
                if not created:
                    return Response({"status": "duplicate", "photo_id": photo.id}, status=200)
                
                # 2. Save Faces with pgvector embeddings using bulk_create for performance
                faces_data = data.get('faces', [])
                faces_to_create = [
                    Face(
                        photo=photo,
                        embedding=f_data.get('embedding'),
                        x=f_data.get('bbox', [0, 0, 0, 0])[0],
                        y=f_data.get('bbox', [0, 0, 0, 0])[1],
                        width=f_data.get('bbox', [0, 0, 0, 0])[2] - f_data.get('bbox', [0, 0, 0, 0])[0],
                        height=f_data.get('bbox', [0, 0, 0, 0])[3] - f_data.get('bbox', [0, 0, 0, 0])[1],
                        detection_confidence=f_data.get('confidence', 1.0)
                    )
                    for f_data in faces_data
                ]
                if faces_to_create:
                    Face.objects.bulk_create(faces_to_create, batch_size=100)
                    
                # 2.5 Categorize photo
                from photos.categorization import categorize_photo
                categorize_photo(photo)
                    
                # 3. Broadcast lightweight event to WebSockets
                photo.refresh_from_db()
                from photos.realtime import broadcast_new_photo
                broadcast_new_photo(photo)
                    
            return Response({"status": "success", "photo_id": photo.id}, status=201)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=400)



class FaceSearchView(APIView):
    throttle_scope = 'face_search'

    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        
        # 1. Validate selfie input file
        if 'file' not in request.FILES:
            return Response({"error": "No selfie image file provided.", "code": "NO_FILE"}, status=400)
            
        file_obj = request.FILES['file']
        
        # 2. Strict validation: bounds (max 10MB) and magic bytes
        max_size = 10 * 1024 * 1024  # 10 MB limit for selfie
        if file_obj.size > max_size:
            return Response({"error": "Selfie image exceeds maximum allowed limit of 10 MB.", "code": "FILE_TOO_LARGE"}, status=400)

        selfie_bytes = file_obj.read()
        try:
            validate_image_file_bytes(selfie_bytes, max_size=max_size)
        except ValueError as val_err:
            audit_log('MALICIOUS_SELFIE_REJECTED', request=request, wedding_slug=slug, details=str(val_err), level='warning')
            return Response({"error": f"Invalid image file: {str(val_err)}", "code": "INVALID_IMAGE"}, status=400)

        # 3. Extract configurable threshold & pagination parameters
        threshold = request.data.get('threshold') or request.query_params.get('threshold')
        page = request.data.get('page') or request.query_params.get('page') or 1
        page_size = request.data.get('page_size') or request.query_params.get('page_size') or 30
        
        # Concurrency Gate: Allow max 2 simultaneous ONNX model inferences on web container
        acquired = _face_search_semaphore.acquire(timeout=2.0)
        if not acquired:
            logger.warning(f"Face search concurrency gate saturated for wedding {slug}")
            return Response({
                "error": "Face search is currently busy processing other guests. Please retry in a moment.",
                "code": "CAPACITY_BUSY"
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        try:
            from faces.face_service import search_photos_by_selfie
            
            result = search_photos_by_selfie(
                wedding=wedding,
                selfie_bytes=selfie_bytes,
                threshold=threshold,
                page=page,
                page_size=page_size
            )
            
            if result.get('status') in ['no_face_detected', 'error']:
                return Response(result, status=400)
                
            return Response(result, status=200)
            
        except Exception as e:
            logger.error(f"Failed to search face: {e}", exc_info=True)
            return Response({"error": f"Failed to search face: {str(e)}"}, status=500)
        finally:
            _face_search_semaphore.release()

class SetReferenceFaceView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)

        # Validate photographer / admin authorization to protect reference biometrics
        from photos.views import authenticate_photographer_or_device
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding, allow_device=False)
        if not is_auth:
            return Response({'error': auth_err or 'Unauthorized to set reference biometrics.'}, status=401)

        role = request.data.get('role') # 'bride' or 'groom'
        
        if role not in ['bride', 'groom']:
            return Response({"error": "Invalid role. Must be 'bride' or 'groom'."}, status=400)
            
        if 'file' not in request.FILES:
            return Response({"error": "No file provided"}, status=400)
            
        file_obj = request.FILES['file']
        max_ref_size = 15 * 1024 * 1024  # 15 MB
        if file_obj.size > max_ref_size:
            return Response({"error": "Reference photo exceeds maximum allowed limit of 15 MB."}, status=400)

        image_bytes = file_obj.read()
        try:
            validate_image_file_bytes(image_bytes, max_size=max_ref_size)
        except ValueError as val_err:
            return Response({"error": f"Invalid reference image: {str(val_err)}"}, status=400)
        
        try:
            from faces.face_service import decode_image_bytes, extract_faces_from_image
            img = decode_image_bytes(image_bytes)
            if img is None:
                return Response({"error": "Could not decode image file."}, status=400)
                
            faces = extract_faces_from_image(img, min_confidence=0.50)
            if not faces:
                return Response({"error": "No face found in reference photo.", "code": "NO_FACE"}, status=400)
                
            target_embedding = faces[0]['embedding']
            
            if role == 'bride':
                wedding.bride_embedding = target_embedding
            else:
                wedding.groom_embedding = target_embedding
                
            wedding.save()
            
            return Response({"status": "success", "message": f"{role.capitalize()} reference face set successfully."})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"Failed to process face: {str(e)}"}, status=500)
