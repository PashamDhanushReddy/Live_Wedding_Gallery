import sys
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
        try:
            subprocess.run(
                'wmic process where "name=\'python.exe\' and commandline like \'%watcher.py%\'" call terminate',
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

        subprocess.Popen([python_exec, "-u", script_path], cwd=base_dir)

def run_startup_recovery():
    import time
    time.sleep(2)  # Allow database connections to finish warming up
    try:
        from .ingestion_service import resume_interrupted_jobs
        resume_interrupted_jobs()
    except Exception as e:
        print(f"Startup job recovery notice: {e}")

class PhotosConfig(AppConfig):
    name = 'photos'

    def ready(self):
        # Only run background worker threads during actual server runtime,
        # never during management commands like makemigrations, migrate, test, collectstatic
        management_commands = {'makemigrations', 'migrate', 'collectstatic', 'test', 'shell', 'dbshell', 'check'}
        is_management = any(cmd in sys.argv for cmd in management_commands)
        if is_management:
            return

        is_server = os.environ.get('RUN_MAIN') == 'true' or 'runserver' in sys.argv or 'daphne' in sys.argv or 'gunicorn' in sys.argv
        if is_server:
            if os.environ.get('ENABLE_WATCHER', 'false').lower() == 'true':
                t_watcher = threading.Thread(target=start_watcher, daemon=True)
                t_watcher.start()

            t_recovery = threading.Thread(target=run_startup_recovery, daemon=True)
            t_recovery.start()
