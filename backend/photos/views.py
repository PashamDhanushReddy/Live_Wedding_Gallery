from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import CameraConnection, Transfer, Photo
from .serializers import CameraConnectionSerializer, TransferSerializer
from weddings.models import Wedding

class CameraConnectView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        data = request.data
        
        # In a real app, you'd generate these or have them statically assigned per wedding
        # For this prototype, we'll accept them or auto-generate them
        host = data.get('host', 'ftp.live-wedding-gallery.com')
        port = data.get('port', 21)
        username = data.get('username', f'camera_{slug}')
        
        connection, created = CameraConnection.objects.update_or_create(
            wedding=wedding,
            defaults={
                'host': host,
                'port': port,
                'username': username,
                'connection_status': 'CONNECTED',
            }
        )
        
        return Response(CameraConnectionSerializer(connection).data)

class CameraDisconnectView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        CameraConnection.objects.filter(wedding=wedding).update(connection_status='DISCONNECTED')
        return Response({"status": "disconnected"})

class CameraFolderView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        folder = request.data.get('folder', 'Uncategorized')
        connection = CameraConnection.objects.filter(wedding=wedding).first()
        if connection:
            connection.active_folder = folder
            connection.save()
            return Response(CameraConnectionSerializer(connection).data)
        return Response({"error": "No camera connection found"}, status=404)

class TransferListView(generics.ListAPIView):
    serializer_class = TransferSerializer
    
    def get_queryset(self):
        slug = self.kwargs.get('slug')
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        return Transfer.objects.filter(camera__wedding=wedding).order_by('-started_at')[:100]

class PhotographerStatsView(APIView):
    def get(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        
        total_photos = Photo.objects.filter(wedding=wedding).count()
        processing = Photo.objects.filter(wedding=wedding, processing_status='PROCESSING').count()
        failed = Photo.objects.filter(wedding=wedding, processing_status='FAILED').count()
        
        connection = CameraConnection.objects.filter(wedding=wedding).first()
        status = connection.connection_status if connection else 'DISCONNECTED'
        
        return Response({
            "total_photos": total_photos,
            "processing": processing,
            "failed": failed,
            "connection_status": status
        })
