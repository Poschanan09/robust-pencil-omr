"""Kaggle Dataset Organizer & Splitter
Course: ICE415 Digital Image Processing (KMUTT)

Processes the real Kaggle OMR dataset from data/archive/:
1. Validates all 145 images against OMR_Ans.csv
2. Splits into Train (100 images, ~70%) and Test (45 images, ~30%) using fixed random seed (42)
3. Copies images to data/kaggle_benchmark/ (all, train, test)
4. Converts wide-format answers to standard project ground_truth.csv (4,350 labeled questions)
5. Generates dataset_summary.json with complete class and split statistics.
"""

from pathlib import Path
import shutil
import json
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ARCHIVE_DIR = DATA_DIR / "archive"
SOURCE_IMG_DIR = ARCHIVE_DIR / "OMR_Image_Resized"
SOURCE_CSV = ARCHIVE_DIR / "OMR_Ans.csv"

BENCHMARK_DIR = DATA_DIR / "kaggle_benchmark"
ALL_IMG_DIR = BENCHMARK_DIR / "images"
TRAIN_IMG_DIR = BENCHMARK_DIR / "train"
TEST_IMG_DIR = BENCHMARK_DIR / "test"


def organize_and_split(train_ratio: float = 0.70, seed: int = 42):
    print("=" * 60)
    print("📦 Organizing Real Kaggle OMR Dataset from data/archive")
    print("=" * 60)

    if not SOURCE_IMG_DIR.exists() or not SOURCE_CSV.exists():
        raise FileNotFoundError(f"Missing source files in {ARCHIVE_DIR}")

    # Create destination directories
    ALL_IMG_DIR.mkdir(parents=True, exist_ok=True)
    TRAIN_IMG_DIR.mkdir(parents=True, exist_ok=True)
    TEST_IMG_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load and clean OMR_Ans.csv
    df = pd.read_csv(SOURCE_CSV).dropna(subset=["Image_ID"])
    df["Image_ID"] = df["Image_ID"].astype(int)
    df = df.sort_values("Image_ID").reset_index(drop=True)

    total_images = len(df)
    print(f"[+] Loaded {total_images} valid sheet records from OMR_Ans.csv")

    # 2. Verify all image files exist
    valid_ids = []
    for img_id in df["Image_ID"]:
        img_file = SOURCE_IMG_DIR / f"{img_id}.jpg"
        if img_file.exists():
            valid_ids.append(img_id)
        else:
            print(f"⚠️  Warning: Missing file {img_file.name}")

    print(f"[+] Verified {len(valid_ids)} image files on disk.")

    # 3. Train / Test Split
    np.random.seed(seed)
    shuffled_ids = np.random.permutation(valid_ids)
    split_idx = int(len(shuffled_ids) * train_ratio)

    train_ids = set(shuffled_ids[:split_idx])
    test_ids = set(shuffled_ids[split_idx:])

    print(f"[+] Split: {len(train_ids)} Train images ({train_ratio*100:.0f}%), {len(test_ids)} Test images ({(1-train_ratio)*100:.0f}%)")

    # 4. Copy image files
    print("[+] Copying images to data/kaggle_benchmark/ ...")
    for img_id in valid_ids:
        src = SOURCE_IMG_DIR / f"{img_id}.jpg"
        # Master copy
        shutil.copy2(src, ALL_IMG_DIR / f"{img_id}.jpg")

        # Split copies
        if img_id in train_ids:
            shutil.copy2(src, TRAIN_IMG_DIR / f"{img_id}.jpg")
        else:
            shutil.copy2(src, TEST_IMG_DIR / f"{img_id}.jpg")

    # 5. Convert to standardized long-format Ground Truth CSV
    print("[+] Converting answers to standard long-format Ground Truth CSV...")
    long_rows = []
    q_cols = [f"Q{i}" for i in range(1, 31)]

    for _, row in df.iterrows():
        img_id = int(row["Image_ID"])
        fname = f"{img_id}.jpg"
        split_name = "train" if img_id in train_ids else "test"

        for q_idx, col in enumerate(q_cols, start=1):
            val = str(row[col]).strip() if pd.notna(row[col]) else "BLANK"

            # Normalize mark condition
            if val == "MULTI":
                condition = "Multi"
                ans = "MULTI"
            elif val == "BLANK" or val == "nan":
                condition = "Blank"
                ans = "BLANK"
            else:
                condition = "Normal"
                ans = val.upper()

            long_rows.append({
                "image_id": fname,
                "question_number": q_idx,
                "correct_answer": ans,
                "mark_condition": condition,
                "split": split_name
            })

    long_df = pd.DataFrame(long_rows)

    # Save to multiple targets for convenience
    gt_main_path = DATA_DIR / "ground_truth.csv"
    gt_benchmark_path = BENCHMARK_DIR / "ground_truth.csv"
    gt_train_path = BENCHMARK_DIR / "train_ground_truth.csv"
    gt_test_path = BENCHMARK_DIR / "test_ground_truth.csv"

    long_df.to_csv(gt_main_path, index=False)
    long_df.to_csv(gt_benchmark_path, index=False)
    long_df[long_df["split"] == "train"].to_csv(gt_train_path, index=False)
    long_df[long_df["split"] == "test"].to_csv(gt_test_path, index=False)

    # 6. Save Dataset Summary JSON
    class_dist = {str(k): int(v) for k, v in long_df["correct_answer"].value_counts().items()}
    summary = {
        "dataset_name": "thejasan/omr-optical-mark-recognition-image-dataset",
        "total_images": int(total_images),
        "total_questions_annotated": int(len(long_df)),
        "questions_per_sheet": 30,
        "options_per_question": 4,
        "image_resolution": "1024x556",
        "splits": {
            "train": {
                "count": int(len(train_ids)),
                "image_ids": sorted([int(x) for x in train_ids])
            },
            "test": {
                "count": int(len(test_ids)),
                "image_ids": sorted([int(x) for x in test_ids])
            }
        },
        "class_distribution": class_dist,
        "directories": {
            "all_images": str(ALL_IMG_DIR.relative_to(PROJECT_ROOT)),
            "train_images": str(TRAIN_IMG_DIR.relative_to(PROJECT_ROOT)),
            "test_images": str(TEST_IMG_DIR.relative_to(PROJECT_ROOT)),
            "ground_truth_csv": str(gt_main_path.relative_to(PROJECT_ROOT))
        }
    }

    with open(BENCHMARK_DIR / "dataset_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print("🎉 Dataset Organization Complete!")
    print(f"  • Total Images: {total_images} (Train: {len(train_ids)}, Test: {len(test_ids)})")
    print(f"  • Total Questions: {len(long_df):,} ground-truth records")
    print(f"  • Ground Truth CSV: {gt_main_path.relative_to(PROJECT_ROOT)}")
    print(f"  • Summary JSON: {(BENCHMARK_DIR / 'dataset_summary.json').relative_to(PROJECT_ROOT)}")
    print("  • Class Distribution:", class_dist)
    print("=" * 60)


if __name__ == "__main__":
    organize_and_split()
