from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from weddings.models import Wedding
from .models import Guest
from rest_framework.parsers import MultiPartParser, FormParser
import tempfile
import os

class GuestRegisterView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, slug, *args, **kwargs):
        try:
            wedding = Wedding.objects.get(slug=slug)
        except Wedding.DoesNotExist:
            return Response({"error": "Wedding not found"}, status=status.HTTP_404_NOT_FOUND)

        consent = request.data.get('consent')
        if consent != 'true':
            return Response({"error": "Consent is required"}, status=status.HTTP_400_BAD_REQUEST)

        selfie_file = request.FILES.get('selfie')
        if not selfie_file:
            return Response({"error": "Selfie image is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Phase 10 - Face Recognition
        from recognition.services import FaceRecognitionService
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            for chunk in selfie_file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
            
        try:
            embedding = FaceRecognitionService.get_embedding(tmp_path)
            if not embedding:
                return Response({"error": "No face detected in selfie"}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
        guest = Guest.objects.create(
            wedding=wedding,
            consent_given=True,
            consent_timestamp=timezone.now(),
            face_embedding=embedding
        )
        
        # Note: Do not save the raw selfie image publicly or persistently

        return Response({
            "session_id": guest.session_id,
            "message": "Registration successful"
        }, status=status.HTTP_201_CREATED)

class GuestDeleteView(APIView):
    def delete(self, request, slug, session_id, *args, **kwargs):
        try:
            guest = Guest.objects.get(session_id=session_id, wedding__slug=slug)
            # Deleting the guest will cascade delete PhotoFace matches
            guest.delete()
            return Response({"message": "Guest data deleted successfully"}, status=status.HTTP_200_OK)
        except Guest.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
