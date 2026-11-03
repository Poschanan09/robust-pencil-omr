"""Kaggle Benchmark Dataset Downloader
Course: ICE415 Digital Image Processing (KMUTT)
Dataset: thejasan/omr-optical-mark-recognition-image-dataset
"""

import os
import sys
import shutil
import glob
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "kaggle_benchmark"

def download_via_kagglehub():
    """Attempt download using kagglehub package."""
    print("🔄 Attempting to download dataset via kagglehub...")
    try:
        import kagglehub
        path = kagglehub.dataset_download("thejasan/omr-optical-mark-recognition-image-dataset")
        print(f"✅ Downloaded to cache path: {path}")
        return Path(path)
    except Exception as e:
        print(f"⚠️  kagglehub download failed or not configured: {e}")
        return None

def download_via_kaggle_cli():
    """Attempt download using kaggle API CLI."""
    print("🔄 Attempting to download dataset via kaggle CLI...")
    try:
        import subprocess
        dataset_name = "thejasan/omr-optical-mark-recognition-image-dataset"
        temp_dir = BASE_DIR / "data" / "temp_kaggle"
        temp_dir.mkdir(parents=True, exist_ok=True)
        cmd = ["kaggle", "datasets", "download", "-d", dataset_name, "-p", str(temp_dir), "--unzip"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"✅ Downloaded and unzipped via Kaggle CLI to {temp_dir}")
            return temp_dir
        else:
            print(f"⚠️  Kaggle CLI returned error: {res.stderr.strip()}")
            return None
    except Exception as e:
        print(f"⚠️  Kaggle CLI not available: {e}")
        return None

def organize_images(source_dir: Path):
    """Filter and copy images to data/kaggle_benchmark."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Search for image files in source_dir recursively
    image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
    found_images = []
    for ext in image_extensions:
        found_images.extend(source_dir.rglob(ext))
    
    # Filter for OMR_Image_Resized if available
    resized_images = [img for img in found_images if "resized" in str(img).lower()]
    target_images = resized_images if resized_images else found_images
    
    if not target_images:
        print("❌ No images found in downloaded source directory.")
        return 0
    
    count = 0
    for img_path in target_images:
        dest_path = DATA_DIR / img_path.name
        if not dest_path.exists():
            shutil.copy2(img_path, dest_path)
            count += 1
            
    print(f"✅ Successfully copied {count} images to {DATA_DIR}")
    return count

def main():
    print("==================================================")
    print("📦 Robust Pencil OMR - Kaggle Benchmark Downloader")
    print("==================================================")
    print(f"Destination: {DATA_DIR}")
    
    src = download_via_kagglehub()
    if not src:
        src = download_via_kaggle_cli()
        
    if src and src.exists():
        count = organize_images(src)
        print(f"\n🎉 Finished: {count} images ready in {DATA_DIR}")
    else:
        print("\n" + "="*50)
        print("ℹ️  MANUAL DOWNLOAD INSTRUCTIONS:")
        print("1. Visit https://www.kaggle.com/datasets/thejasan/omr-optical-mark-recognition-image-dataset")
        print("2. Download and unzip the archive.")
        print(f"3. Copy the images (e.g. from OMR_Image_Resized) into:\n   {DATA_DIR}")
        print("="*50)

if __name__ == "__main__":
    main()
