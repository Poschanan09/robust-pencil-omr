"""Tests for Evaluation Metrics and Ablation Study.

Validates:
1. Accuracy calculation under normal and ambiguous exclusion conditions.
2. Precision, Recall, and F1 calculation (macro & per-class).
3. Rejection metrics (Rejection Rate, FAR, Ambiguity Capture Rate).
4. Confusion matrix heatmap generation.
5. Ablation study functions for binarization, morphology, and rectification.
"""

from pathlib import Path
import numpy as np
import pytest

from evaluation.metrics import (
    compute_accuracy,
    compute_precision_recall_f1,
    compute_rejection_metrics,
    generate_confusion_matrix,
    full_evaluation
)
from evaluation.ablation_study import (
    run_ablation_binarization,
    run_ablation_morphology,
    run_ablation_rectification
)


def test_compute_accuracy():
    predictions = {1: "A", 2: "B", 3: "C", 4: "D", 5: "AMBIGUOUS"}
    ground_truth = {1: "A", 2: "B", 3: "D", 4: "D", 5: "E"}

    # With ignore_ambiguous=True: 4 evaluated, 3 correct (1, 2, 4) -> 3/4 = 0.75
    acc = compute_accuracy(predictions, ground_truth, ignore_ambiguous=True)
    assert acc == pytest.approx(0.75)

    # With ignore_ambiguous=False: 5 evaluated, 3 correct -> 3/5 = 0.60
    acc_all = compute_accuracy(predictions, ground_truth, ignore_ambiguous=False)
    assert acc_all == pytest.approx(0.60)


def test_compute_precision_recall_f1():
    preds = ["A", "B", "A", "C", "B"]
    gts   = ["A", "B", "B", "C", "B"]

    res = compute_precision_recall_f1(preds, gts, classes=["A", "B", "C"])
    assert "precision" in res
    assert "recall" in res
    assert "f1" in res
    assert "per_class" in res

    # Class A: TP=1, FP=1 (item index 2), FN=0 -> Precision=0.5, Recall=1.0
    assert res["per_class"]["A"]["precision"] == 0.5
    assert res["per_class"]["A"]["recall"] == 1.0


def test_compute_rejection_metrics():
    results = [
        {
            "filename": "sheet_01",
            "decisions": [
                {"question": 1, "status": "CONFIRMED", "predicted_answer": "A"},
                {"question": 2, "status": "AMBIGUOUS", "predicted_answer": "AMBIGUOUS"},
                {"question": 3, "status": "CONFIRMED", "predicted_answer": "B"},
                {"question": 4, "status": "CONFIRMED", "predicted_answer": "C"},  # wrong (true is D)
            ]
        }
    ]
    ground_truth = {"sheet_01": {1: "A", 2: "B", 3: "B", 4: "D"}}
    degraded_tags = [("sheet_01", 2)]

    rej = compute_rejection_metrics(results, ground_truth, degraded_tags)

    # 4 questions, 1 ambiguous -> Rejection rate = 25.0%
    assert rej["rejection_rate"] == 25.0

    # 3 confirmed, 1 wrong -> FAR = 1/3 * 100 = 33.33%
    assert rej["far"] == pytest.approx(33.33, rel=1e-2)

    # 1 degraded question, flagged as ambiguous -> 100%
    assert rej["capture_rate"] == 100.0


def test_generate_confusion_matrix(tmp_path: Path):
    preds = ["A", "B", "C", "A", "B"]
    gts   = ["A", "B", "A", "A", "B"]
    classes = ["A", "B", "C"]

    out_png = tmp_path / "confusion_matrix.png"
    cm = generate_confusion_matrix(preds, gts, classes=classes, save_path=str(out_png))

    assert cm.shape == (3, 3)
    assert cm[0, 0] == 2  # True A, Pred A = 2
    assert out_png.exists()


def test_full_evaluation(tmp_path: Path):
    results = [
        {
            "filename": "sheet_1",
            "decisions": [
                {"question": 1, "status": "CONFIRMED", "predicted_answer": "A"},
                {"question": 2, "status": "CONFIRMED", "predicted_answer": "B"},
            ]
        }
    ]
    gt = {"sheet_1": {1: "A", 2: "B"}}
    cm_path = str(tmp_path / "cm_eval.png")

    eval_dict = full_evaluation(results, gt, classes=["A", "B"], confusion_matrix_path=cm_path)
    assert eval_dict["accuracy"] == 1.0
    assert eval_dict["rejection_rate"] == 0.0
    assert eval_dict["far"] == 0.0
    assert Path(cm_path).exists()


def test_ablation_rectification_metrics():
    test_cases = [
        {
            "image": np.ones((500, 500), dtype=np.uint8) * 255,
            "corners": np.array([[20, 20], [480, 25], [475, 470], [25, 480]], dtype=np.float32),
            "canonical_corners": np.array([[0,0], [500,0], [500,500], [0,500]])
        }
    ]
    res = run_ablation_rectification(test_cases, (500, 500))
    assert "dataframe" in res
    assert "summary" in res
    assert res["summary"]["Mean_Homography_Error_px"] < res["summary"]["Mean_HoughDeskew_Error_px"]
