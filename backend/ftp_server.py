import os
import sys
import django
import logging
import asyncio
from pathlib import Path
from pyftpdlib.authorizers import DummyAuthorizer, AuthenticationFailed
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import cloudinary
import cloudinary.uploader
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from dotenv import load_dotenv

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from weddings.models import Wedding
from photos.models import Photo, CameraConnection, Transfer
from faces.models import Face
from photos.serializers import PhotoSerializer, TransferSerializer
import threading
import uuid
import datetime
from django.utils import timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ftp_server")

# Load environment
load_dotenv(BASE_DIR.parent / '.env')
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME') or os.environ.get('CLOUDINARY_1_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY') or os.environ.get('CLOUDINARY_1_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET') or os.environ.get('CLOUDINARY_1_API_SECRET')
)

class DjangoAuthorizer(DummyAuthorizer):
    def validate_authentication(self, username, password, handler):
        # Authenticate against CameraConnection
        try:
            # We use the wedding slug as the password for simplicity, or hardcoded for now
            # In a real app, query CameraConnection for username/password
            connection = CameraConnection.objects.get(username=username)
            # Update connection status
            connection.connection_status = 'CONNECTED'
            connection.last_connected = timezone.now()
            connection.save()
            return True
        except CameraConnection.DoesNotExist:
            raise AuthenticationFailed("Invalid username or password.")

class WeddingFTPHandler(FTPHandler):
    authorizer = DjangoAuthorizer()
    
    def on_file_received(self, file_path):
        logger.info(f"Received file: {file_path}")
        # Run processing in a thread so we don't block FTP
        threading.Thread(target=self.process_photo, args=(self.username, file_path)).start()

    def process_photo(self, username, file_path):
        try:
            connection = CameraConnection.objects.get(username=username)
            wedding = connection.wedding
            
            # Create Transfer record
            filename = os.path.basename(file_path)
            transfer = Transfer.objects.create(
                camera=connection,
                filename=filename,
                status='UPLOADING',
                progress=0
            )
            
            self.broadcast_transfer(wedding.slug, transfer)

            # 1. Upload to Cloudinary
            logger.info(f"Uploading {filename} to Cloudinary folder {connection.active_folder}...")
            transfer.progress = 50
            transfer.save()
            self.broadcast_transfer(wedding.slug, transfer)

            upload_result = cloudinary.uploader.upload(
                file_path,
                folder=f"weddings/{wedding.slug}/{connection.active_folder}/originals"
            )
            
            # 2. Save Photo in Django
            logger.info(f"Saving {filename} to DB...")
            photo = Photo.objects.create(
                wedding=wedding,
                original_filename=filename,
                cloudinary_public_id=upload_result.get('public_id'),
                secure_url=upload_result.get('secure_url'),
                cloudinary_url=upload_result.get('url'),
                width=upload_result.get('width'),
                height=upload_result.get('height'),
                file_size=upload_result.get('bytes'),
                folder=connection.active_folder,
                processing_status='PROCESSING', # Need face detection
                upload_status='COMPLETED',
                captured_at=timezone.now()
            )
            
            transfer.photo = photo
            transfer.status = 'UPLOADED'
            transfer.progress = 100
            transfer.completed_at = timezone.now()
            transfer.save()
            
            connection.last_photo_received = timezone.now()
            connection.save()
            
            self.broadcast_transfer(wedding.slug, transfer)
            
            # 3. Trigger Face Recognition
            # In a real app this would be a Celery task. For prototype, do it synchronously or background thread.
            self.extract_faces(photo, file_path)
            
            # Broadcast new photo
            photo.processing_status = 'COMPLETED'
            photo.save()
            
            channel_layer = get_channel_layer()
            photo_data = PhotoSerializer(photo).data
            async_to_sync(channel_layer.group_send)(
                f'wedding_{wedding.slug}',
                {
                    'type': 'new_photo',
                    'photo': photo_data
                }
            )
            
            # Clean up local file
            os.remove(file_path)
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            if 'transfer' in locals():
                transfer.status = 'FAILED'
                transfer.error_message = str(e)
                transfer.save()
                self.broadcast_transfer(wedding.slug, transfer)

    def broadcast_transfer(self, slug, transfer):
        channel_layer = get_channel_layer()
        transfer_data = TransferSerializer(transfer).data
        async_to_sync(channel_layer.group_send)(
            f'wedding_{slug}',
            {
                'type': 'transfer_update',
                'transfer': transfer_data
            }
        )

    def extract_faces(self, photo, file_path):
        try:
            import cv2
            from insightface.app import FaceAnalysis
            
            app = FaceAnalysis(name='buffalo_l')
            app.prepare(ctx_id=0, det_size=(640, 640))
            
            img = cv2.imread(file_path)
            faces = app.get(img)
            
            for face in faces:
                bbox = face.bbox
                embedding = face.embedding.tolist()
                
                Face.objects.create(
                    photo=photo,
                    embedding=embedding,
                    x=bbox[0],
                    y=bbox[1],
                    width=bbox[2] - bbox[0],
                    height=bbox[3] - bbox[1],
                    detection_confidence=face.det_score
                )
        except Exception as e:
            logger.error(f"Face extraction failed: {e}")


def main():
    # Setup temporary directory for FTP uploads
    ftp_dir = os.path.join(BASE_DIR, 'media', 'ftp_uploads')
    os.makedirs(ftp_dir, exist_ok=True)
    
    # We dynamically load authorizers, but pyftpdlib DummyAuthorizer expects local directories.
    # We will override this by creating a dynamic directory per user if needed, or just map everyone to ftp_dir
    authorizer = DjangoAuthorizer()
    
    # Pre-populate authorizer with existing connections to allow login
    for conn in CameraConnection.objects.all():
        try:
            authorizer.add_user(conn.username, 'password123', ftp_dir, perm='elradfmwMT')
        except Exception:
            pass

    handler = WeddingFTPHandler
    handler.authorizer = authorizer
    
    address = ('0.0.0.0', 2121) # using 2121 to avoid root port restrictions
    server = FTPServer(address, handler)
    
    logger.info(f"Starting Cloud FTP Server on {address[0]}:{address[1]}...")
    server.serve_forever()

if __name__ == '__main__':
    main()
