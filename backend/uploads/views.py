from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from weddings.models import Wedding
from .services import PhotoUploadService
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser

class PhotoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, slug, *args, **kwargs):
        try:
            wedding = Wedding.objects.get(slug=slug)
        except Wedding.DoesNotExist:
            return Response({"error": "Wedding not found"}, status=status.HTTP_404_NOT_FOUND)

        file_obj = request.FILES.get('photo')
        if not file_obj:
            return Response({"error": "No photo provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file format (basic check)
        allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/heic']
        if file_obj.content_type not in allowed_types:
             return Response({"error": "Invalid file type. Allowed: JPEG, PNG, WEBP, HEIC."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file size
        max_size_mb = getattr(settings, 'MAX_UPLOAD_SIZE_MB', 20)
        if file_obj.size > int(max_size_mb) * 1024 * 1024:
            return Response({"error": f"File too large. Max {max_size_mb}MB allowed."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            photo, created = PhotoUploadService.process_upload(wedding, file_obj, file_obj.name)
            
            return Response({
                "id": photo.id,
                "url": photo.thumbnail_url,
                "created": created,
                "status": photo.status
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
