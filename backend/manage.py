#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
        
    if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
        import subprocess
        import atexit
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        watcher_script = os.path.join(base_dir, 'uploader', 'watcher.py')
        
        print("Starting background watcher.py...")
        watcher_process = subprocess.Popen([sys.executable, watcher_script], cwd=os.path.join(base_dir, 'uploader'))
        
        def kill_watcher():
            print("Stopping watcher.py...")
            watcher_process.terminate()
            
        atexit.register(kill_watcher)

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
