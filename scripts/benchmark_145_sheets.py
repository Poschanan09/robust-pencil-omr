"""Benchmark all 145 sheets from Kaggle dataset."""

from pathlib import Path
import sys
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from omr.pipeline import OMRPipeline

df = pd.read_csv(PROJECT_ROOT / "data" / "archive" / "OMR_Ans.csv")
img_dir = PROJECT_ROOT / "data" / "archive" / "OMR_Image_Resized"

pipeline = OMRPipeline()

total_questions = 0
correct_confirmed = 0
total_ambiguous = 0
correct_with_guess = 0
sheet_scores = []
problematic_sheets = []

for img_id in range(1, 146):
    img_path = img_dir / f"{img_id}.jpg"
    if not img_path.exists():
        continue
    gt_row = df[df["Image_ID"] == img_id].iloc[0, 1:31].tolist()

    res = pipeline.process_single_image(img_path)
    if res["status"] != "success":
        print(f"Sheet {img_id:03d} REJECTED: {res.get('rejection_reason')}")
        continue

    s_corr = 0
    s_guess_corr = 0
    for d, gt in zip(res["results"], gt_row):
        pred = d["answer"]
        guess = d["tentative_guess"]
        total_questions += 1
        if d["status"] == "AMBIGUOUS":
            total_ambiguous += 1
            if guess == gt:
                s_guess_corr += 1
                correct_with_guess += 1
        elif pred == gt:
            s_corr += 1
            correct_confirmed += 1
            correct_with_guess += 1

    sheet_scores.append((img_id, s_corr, len(res["results"])))
    if (s_corr + s_guess_corr) < 28:
        problematic_sheets.append((img_id, s_corr, s_corr + s_guess_corr))
        print(f"Sheet {img_id:03d}: Confirmed {s_corr}/30, With Guess {s_corr + s_guess_corr}/30")

print("\n" + "=" * 50)
print("=== OVERALL DATASET BENCHMARK (145 SHEETS) ===")
print("=" * 50)
print(f"Total Questions Evaluated: {total_questions}")
print(f"Direct Confirmed Correct: {correct_confirmed}/{total_questions} ({correct_confirmed/total_questions*100:.2f}%)")
print(f"Ambiguous / Flagged for Review: {total_ambiguous}/{total_questions} ({total_ambiguous/total_questions*100:.2f}%)")
print(f"Total Accuracy with Human/Guess: {correct_with_guess}/{total_questions} ({correct_with_guess/total_questions*100:.2f}%)")
print(f"Sheets with < 28/30 accuracy: {problematic_sheets}")
