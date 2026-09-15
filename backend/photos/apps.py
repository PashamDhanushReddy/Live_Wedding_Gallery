import os
import subprocess
import threading
from django.apps import AppConfig

def start_watcher():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script_path = os.path.join(base_dir, 'uploader', 'watcher.py')
    python_exec = os.path.join(base_dir, 'venv', 'Scripts', 'python.exe')
    
    if os.path.exists(script_path) and os.path.exists(python_exec):
        print(f"\n--- Automatically starting Photo Uploader Watcher ---")
        
        # Kill any existing orphaned watcher processes first (Windows specific)
        try:
            subprocess.run(
                'wmic process where "name=\'python.exe\' and commandline like \'%watcher.py%\'" call terminate',
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

        subprocess.Popen([python_exec, "-u", script_path], cwd=base_dir)
    else:
        print(f"\nCould not find watcher script or python exec. Paths: {script_path}, {python_exec}")

class PhotosConfig(AppConfig):
    name = 'photos'

    def ready(self):
        # Prevent running twice due to Django's autoreloader
        if os.environ.get('RUN_MAIN') == 'true':
            t = threading.Thread(target=start_watcher)
            t.daemon = True
            t.start()
