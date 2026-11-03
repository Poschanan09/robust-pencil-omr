"""Evaluation metrics module for Optical Mark Recognition (OMR).

Calculates standard classification metrics (Accuracy, Precision, Recall, F1-Score),
Human-in-the-Loop Rejection metrics (Rejection Rate, False Acceptance Rate - FAR,
Ambiguity Capture Rate), and Confusion Matrix visualization using Seaborn.

References:
- ICE415 Digital Image Processing, KMUTT
- Powers, D. M. (2020). Evaluation: from precision, recall and F-measure to ROC,
  informedness, markedness and correlation.
- Chow, C. (1970). On optimum recognition error and reject tradeoff.
  IEEE Transactions on Information Theory, 16(1), 41-46.
"""

from typing import Dict, List, Optional, Tuple, Union, Any
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless server execution
import matplotlib.pyplot as plt
import seaborn as sns


def compute_accuracy(
    predictions: Union[Dict[int, str], List[str]],
    ground_truth: Union[Dict[int, str], List[str]],
    ignore_ambiguous: bool = True
) -> float:
    """Compute overall classification accuracy.

    Formula:
        Accuracy = (TP + TN) / (Total Evaluated)

    Args:
        predictions: Predicted answers mapped by question index or as list.
        ground_truth: Ground truth answers mapped by question index or as list.
        ignore_ambiguous: If True, exclude predictions labeled 'AMBIGUOUS' or '?'
                         from the denominator.

    Returns:
        Accuracy score between 0.0 and 1.0. (Returns 0.0 if no items evaluated)
    """
    if isinstance(predictions, list) and isinstance(ground_truth, list):
        keys = list(range(min(len(predictions), len(ground_truth))))
        pred_dict = {i: predictions[i] for i in keys}
        gt_dict = {i: ground_truth[i] for i in keys}
    else:
        pred_dict = predictions  # type: ignore
        gt_dict = ground_truth    # type: ignore

    common_keys = sorted(set(pred_dict.keys()).intersection(set(gt_dict.keys())))
    if not common_keys:
        return 0.0

    correct = 0
    total = 0

    for k in common_keys:
        pred = pred_dict[k]
        gt = gt_dict[k]

        if ignore_ambiguous and pred in ("AMBIGUOUS", "?", None):
            continue

        total += 1
        if pred == gt:
            correct += 1

    return correct / total if total > 0 else 0.0


def compute_precision_recall_f1(
    predictions: Union[Dict[int, str], List[str]],
    ground_truth: Union[Dict[int, str], List[str]],
    classes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Compute per-class and macro-averaged Precision, Recall, and F1-score.

    Formulas:
        Precision_c = TP_c / (TP_c + FP_c)
        Recall_c    = TP_c / (TP_c + FN_c)
        F1_c        = 2 * Precision_c * Recall_c / (Precision_c + Recall_c)

        Macro_Precision = (1/|C|) * sum(Precision_c)
        Macro_Recall    = (1/|C|) * sum(Recall_c)
        Macro_F1        = (1/|C|) * sum(F1_c)

    Args:
        predictions: Predicted answers.
        ground_truth: Ground truth answers.
        classes: Distinct class labels (defaults to sorted unique labels present).

    Returns:
        Dict containing:
            - "precision": Macro-average precision
            - "recall": Macro-average recall
            - "f1": Macro-average F1-score
            - "per_class": Dict of metrics per class
    """
    if isinstance(predictions, list) and isinstance(ground_truth, list):
        keys = list(range(min(len(predictions), len(ground_truth))))
        y_pred = [predictions[i] for i in keys]
        y_true = [ground_truth[i] for i in keys]
    else:
        common_keys = sorted(set(predictions.keys()).intersection(set(ground_truth.keys())))
        y_pred = [predictions[k] for k in common_keys]
        y_true = [ground_truth[k] for k in common_keys]

    if not y_true:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "per_class": {}}

    if classes is None:
        classes = sorted(list(set(y_true).union(set(y_pred))))

    per_class = {}
    precisions = []
    recalls = []
    f1s = []

    for c in classes:
        tp = sum(1 for p, t in zip(y_pred, y_true) if p == c and t == c)
        fp = sum(1 for p, t in zip(y_pred, y_true) if p == c and t != c)
        fn = sum(1 for p, t in zip(y_pred, y_true) if p != c and t == c)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        per_class[str(c)] = {
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1": round(float(f1), 4),
            "support": sum(1 for t in y_true if t == c)
        }
        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)

    return {
        "precision": round(float(np.mean(precisions)), 4) if precisions else 0.0,
        "recall": round(float(np.mean(recalls)), 4) if recalls else 0.0,
        "f1": round(float(np.mean(f1s)), 4) if f1s else 0.0,
        "per_class": per_class
    }


def compute_rejection_metrics(
    results: List[Dict[str, Any]],
    ground_truth: Optional[Dict[str, Dict[int, str]]] = None,
    degraded_question_tags: Optional[List[Tuple[str, int]]] = None
) -> Dict[str, float]:
    """Compute Human-in-the-Loop Rejection metrics.

    Mathematical Definitions (Chow's Pattern Rejection Framework):
        1. Rejection Rate:
           RR = (N_ambiguous / N_total) * 100%
        2. False Acceptance Rate (FAR):
           FAR = (N_wrong_confirmed / N_confirmed) * 100%
        3. Ambiguity Capture Rate:
           ACR = (N_degraded_flagged_as_ambiguous / N_total_degraded) * 100%

    Args:
        results: List of result dicts from pipeline execution. Each item
                 has "status" or "decisions" containing questions with
                 "status" ('CONFIRMED' vs 'AMBIGUOUS') and "predicted_answer".
        ground_truth: Optional mapping of filename/id -> {question_num: correct_answer}.
        degraded_question_tags: Optional list of (image_id, question_num) known to
                               have faint marks, smudges, or partial erasures.

    Returns:
        Dict with "rejection_rate", "far", and "capture_rate" (in percentage 0-100).
    """
    total_questions = 0
    total_ambiguous = 0
    total_confirmed = 0
    wrong_confirmed = 0

    degraded_flagged = 0
    total_degraded = len(degraded_question_tags) if degraded_question_tags else 0
    degraded_set = set(degraded_question_tags) if degraded_question_tags else set()

    for item in results:
        image_id = item.get("filename", item.get("image_id", "unknown"))
        decisions = item.get("decisions", [])

        # If decisions is dict mapping q_num -> data
        if isinstance(decisions, dict):
            decision_items = [{"question": k, **v} for k, v in decisions.items()]
        else:
            decision_items = decisions

        gt_for_image = ground_truth.get(image_id, {}) if ground_truth else {}

        for dec in decision_items:
            q_num = dec.get("question", 0)
            status = dec.get("status", "CONFIRMED")
            pred = dec.get("predicted_answer", dec.get("answer", dec.get("choice", None)))

            total_questions += 1

            if status == "AMBIGUOUS" or pred in ("AMBIGUOUS", "?"):
                total_ambiguous += 1
                if (image_id, q_num) in degraded_set:
                    degraded_flagged += 1
            else:
                total_confirmed += 1
                if gt_for_image and q_num in gt_for_image:
                    correct_ans = gt_for_image[q_num]
                    if pred != correct_ans:
                        wrong_confirmed += 1

    rejection_rate = (total_ambiguous / total_questions * 100.0) if total_questions > 0 else 0.0
    far = (wrong_confirmed / total_confirmed * 100.0) if total_confirmed > 0 else 0.0
    capture_rate = (degraded_flagged / total_degraded * 100.0) if total_degraded > 0 else 100.0

    return {
        "rejection_rate": round(float(rejection_rate), 2),
        "far": round(float(far), 2),
        "capture_rate": round(float(capture_rate), 2)
    }


def generate_confusion_matrix(
    predictions: List[str],
    ground_truth: List[str],
    classes: Optional[List[str]] = None,
    save_path: Optional[str] = None,
    title: str = "OMR Classification Confusion Matrix"
) -> np.ndarray:
    """Generate and plot a Seaborn heatmap confusion matrix.

    Args:
        predictions: List of predicted labels.
        ground_truth: List of true labels.
        classes: Ordered list of class labels (e.g., ['A', 'B', 'C', 'D', 'E', 'BLANK', 'AMBIGUOUS']).
        save_path: File path to save the generated PNG plot.
        title: Plot title.

    Returns:
        2D numpy array confusion matrix where rows are True and columns are Predicted.
    """
    if classes is None:
        classes = sorted(list(set(ground_truth).union(set(predictions))))

    class_to_idx = {c: i for i, c in enumerate(classes)}
    n = len(classes)
    cm = np.zeros((n, n), dtype=int)

    for true_label, pred_label in zip(ground_truth, predictions):
        if true_label in class_to_idx and pred_label in class_to_idx:
            cm[class_to_idx[true_label], class_to_idx[pred_label]] += 1

    if save_path:
        plt.figure(figsize=(8, 6))
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=classes,
            yticklabels=classes,
            cbar=True
        )
        plt.title(title, fontsize=14, fontweight="bold", pad=12)
        plt.xlabel("Predicted Choice", fontsize=11, labelpad=8)
        plt.ylabel("True Choice", fontsize=11, labelpad=8)
        plt.tight_layout()
        plt.savefig(save_path, dpi=300)
        plt.close()

    return cm


def full_evaluation(
    results: List[Dict[str, Any]],
    ground_truth: Dict[str, Dict[int, str]],
    classes: Optional[List[str]] = None,
    confusion_matrix_path: Optional[str] = None
) -> Dict[str, Any]:
    """Run full evaluation suite combining all metrics.

    Args:
        results: Batch pipeline results.
        ground_truth: Nested dict mapping filename -> {question_num: correct_choice}.
        classes: Allowed classes (e.g. ['A', 'B', 'C', 'D', 'E']).
        confusion_matrix_path: Optional path to save confusion matrix heatmap PNG.

    Returns:
        Comprehensive dictionary containing:
            - accuracy: Overall accuracy on confirmed predictions
            - precision: Macro precision
            - recall: Macro recall
            - f1: Macro F1
            - rejection_rate: Percentage flagged for review
            - far: False acceptance rate on confirmed items
            - capture_rate: Ambiguity capture rate
            - per_class: Breakdown per choice
            - total_evaluated: Count of evaluated questions
    """
    y_pred = []
    y_true = []

    for item in results:
        img_id = item.get("filename", item.get("image_id", ""))
        gt_sheet = ground_truth.get(img_id, {})
        decisions = item.get("decisions", [])

        if isinstance(decisions, dict):
            decisions = [{"question": k, **v} for k, v in decisions.items()]

        for dec in decisions:
            q_num = dec.get("question", 0)
            pred = dec.get("predicted_answer", dec.get("answer", "AMBIGUOUS"))
            if q_num in gt_sheet:
                y_pred.append(pred)
                y_true.append(gt_sheet[q_num])

    acc = compute_accuracy(y_pred, y_true, ignore_ambiguous=True)
    clf_metrics = compute_precision_recall_f1(y_pred, y_true, classes=classes)
    rej_metrics = compute_rejection_metrics(results, ground_truth)

    cm = None
    if confusion_matrix_path:
        cm = generate_confusion_matrix(
            y_pred, y_true, classes=classes, save_path=confusion_matrix_path
        )

    return {
        "accuracy": round(float(acc), 4),
        "precision": clf_metrics["precision"],
        "recall": clf_metrics["recall"],
        "f1": clf_metrics["f1"],
        "rejection_rate": rej_metrics["rejection_rate"],
        "far": rej_metrics["far"],
        "capture_rate": rej_metrics["capture_rate"],
        "per_class": clf_metrics["per_class"],
        "total_evaluated": len(y_true),
        "confusion_matrix": cm.tolist() if cm is not None else None
    }
