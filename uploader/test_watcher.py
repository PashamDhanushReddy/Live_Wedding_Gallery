import os
import time
import threading
import sys

# Override env before import
os.environ['WATCH_FOLDER'] = os.path.join(os.path.dirname(__file__), 'test_watch_folder')
os.environ['FILE_STABLE_CHECK_INTERVAL'] = '1'
os.environ['FILE_STABLE_CHECK_COUNT'] = '2'

from watcher import start_watching

def simulate_slow_camera_copy():
    watch_folder = os.environ['WATCH_FOLDER']
    os.makedirs(watch_folder, exist_ok=True)
    
    time.sleep(2) # Give watcher time to start
    
    test_file = os.path.join(watch_folder, 'IMG_001.JPG')
    print(f"Simulating slow copy to {test_file}...")
    
    with open(test_file, 'wb') as f:
        f.write(b"Chunk 1...")
        f.flush()
        time.sleep(2.5) # Simulate delay
        f.write(b"Chunk 2...")
        f.flush()
        
    print("Finished writing test file.")
    time.sleep(5) # Give processor time to finish
    print("Test complete.")
    # Exit process
    os._exit(0)

if __name__ == '__main__':
    t = threading.Thread(target=simulate_slow_camera_copy)
    t.daemon = True
    t.start()
    
    start_watching()
