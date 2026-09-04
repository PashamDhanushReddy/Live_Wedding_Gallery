import os
import time
import shutil
import argparse
import random
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="Wedding Camera Simulator")
    parser.add_argument('--interval', type=int, default=5, help="Seconds between simulated photos (default 5)")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    samples_dir = os.path.join(base_dir, 'samples')
    incoming_dir = os.path.join(base_dir, 'incoming')

    os.makedirs(samples_dir, exist_ok=True)
    os.makedirs(incoming_dir, exist_ok=True)

    samples = [f for f in os.listdir(samples_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    if not samples:
        print(f"Error: No sample images found in {samples_dir}")
        print("Please place some sample images in the samples directory before running.")
        return

    print(f"Started Camera Simulator. Capturing every {args.interval} seconds.")
    print("Press Ctrl+C to stop.")

    photo_counter = 1
    
    try:
        while True:
            sample = random.choice(samples)
            source_path = os.path.join(samples_dir, sample)
            
            # Generate a realistic unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = os.path.splitext(sample)[1]
            new_filename = f"DSC_{timestamp}_{photo_counter:04d}{ext}"
            dest_path = os.path.join(incoming_dir, new_filename)
            
            # Copy file to simulate taking a photo
            shutil.copy2(source_path, dest_path)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Captured {new_filename} (from {sample})")
            
            photo_counter += 1
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\nSimulator stopped.")

if __name__ == "__main__":
    main()
