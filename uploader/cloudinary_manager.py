import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class CloudinaryManager:
    def __init__(self):
        accounts_str = os.environ.get('CLOUDINARY_ACCOUNTS', '')
        self.accounts = [acc.strip() for acc in accounts_str.split(',') if acc.strip()]
        self.current_account_idx = 0
        
        if not self.accounts:
            print("WARNING: No Cloudinary accounts configured.")

    def _configure_current_account(self):
        if not self.accounts:
            return False
            
        current_url = self.accounts[self.current_account_idx]
        os.environ['CLOUDINARY_URL'] = current_url
        
        import re
        match = re.match(r"cloudinary://([^:]+):([^@]+)@(.+)", current_url)
        if match:
            api_key, api_secret, cloud_name = match.groups()
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True
            )
        return True

    def rotate_account(self):
        """Switch to the next account in the pool."""
        if not self.accounts:
            return False
            
        self.current_account_idx += 1
        if self.current_account_idx >= len(self.accounts):
            print("CRITICAL: All Cloudinary accounts have been exhausted!")
            self.current_account_idx = 0 # Wrap around, but ideally alert
            return False
            
        print(f"Rotating to Cloudinary Account index {self.current_account_idx}")
        return True

    def upload_image(self, file_path):
        """Uploads an image, retrying on backup accounts if quota errors occur."""
        if not self._configure_current_account():
            return None

        upload_path = file_path
        temp_path = None
        
        # Target 1-2 MB for optimal loading speed and quality
        file_size = os.path.getsize(file_path)
        if file_size > 2 * 1024 * 1024:
            print(f"File {file_path} is {file_size/1024/1024:.2f}MB. Compressing to ~1-2MB...")
            try:
                from PIL import Image
                import tempfile
                
                with Image.open(file_path) as img:
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                        
                    # Calculate new size while preserving aspect ratio
                    # Max dimension 2560px for high clarity but smaller size
                    max_dim = 2560
                    if max(img.size) > max_dim:
                        ratio = max_dim / max(img.size)
                        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                        img = img.resize(new_size, Image.Resampling.LANCZOS)
                        
                    temp_fd, temp_path = tempfile.mkstemp(suffix=".jpg")
                    os.close(temp_fd)
                    
                    # Save with quality 85 to retain good clarity
                    img.save(temp_path, format="JPEG", quality=85, optimize=True)
                    
                    new_size = os.path.getsize(temp_path)
                    print(f"Compressed to {new_size/1024/1024:.2f}MB")
                    upload_path = temp_path
            except Exception as e:
                print(f"Failed to compress {file_path}: {e}")
                # We'll try uploading the original anyway, but it will likely fail.

        while True:
            try:
                print(f"Uploading {file_path} to Cloudinary (Account {self.current_account_idx})...")
                # Eagerly generate a thumbnail transformation
                response = cloudinary.uploader.upload(
                    upload_path,
                    folder="live_wedding_album",
                    eager=[
                        {"width": 800, "crop": "scale", "quality": "auto"}
                    ],
                    timeout=20
                )
                
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
                
                # Cloudinary Response has 'public_id', 'secure_url', 'eager' (for thumbnails)
                thumbnail_url = response.get('secure_url')
                if 'eager' in response and len(response['eager']) > 0:
                    thumbnail_url = response['eager'][0].get('secure_url', thumbnail_url)
                
                return {
                    'public_id': response.get('public_id'),
                    'secure_url': response.get('secure_url'),
                    'thumbnail_url': thumbnail_url,
                    'width': response.get('width'),
                    'height': response.get('height'),
                    'bytes': response.get('bytes')
                }

            except Exception as e:
                error_msg = str(e).lower()
                print(f"Cloudinary upload failed: {error_msg}")
                # Check for quota/rate limit indicators
                if "quota" in error_msg or "limit" in error_msg or "storage" in error_msg or "400" in error_msg or "401" in error_msg:
                    print("Possible quota limit reached. Failing over to next account...")
                    if not self.rotate_account():
                        print("Failed to rotate account. Giving up.")
                        return None
                    self._configure_current_account()
                else:
                    # Other network error, don't burn an account
                    print("Upload error is not quota related. Failing upload.")
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)
                    return None

# Singleton instance
cloudinary_manager = CloudinaryManager()
