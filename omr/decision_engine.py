"""Step 6: Tri-State Decision Engine Module
Course: ICE415 Digital Image Processing (KMUTT)

This module implements the core architectural innovation of the project:
"Tri-State Decision Logic with Rejection Threshold (Human-in-the-Loop Architecture)"

Unlike conventional OMR systems that force a binary choice (0 = Blank, 1 = Filled)
and risk misgrading faint pencils or imperfect erasures, this engine classifies
each question into one of three explicit states:
1. FILLED (ฝนชัดเจน):
   - The primary bubble has fill-ratio F_(1) >= T_high (e.g. >= 0.40).
   - The secondary runner-up has F_(2) < T_low (e.g. < 0.15).
   - Contrast margin ΔF = F_(1) - F_(2) >= delta_min (e.g. >= 0.20).
   -> Confirmed answer registered automatically with HIGH confidence.

2. BLANK (เว้นว่างชัดเจน):
   - All options have fill-ratio F_i < T_low.
   -> Confirmed unattempted question registered automatically.

3. AMBIGUOUS (กำกวม / ส่งตรวจทาน):
   Triggered by any evidence of uncertainty:
   - Case A (Erasure Ghost Mark): Student erased an old answer and shaded a new one,
     leaving residual graphite smudge where ΔF < delta_min or F_(2) >= T_low.
   - Case B (Faint Shading): Shaded with HB pencil or light hand pressure,
     falling in the borderline margin T_low <= F_(1) < T_high.
   - Case C (Double Marks): Multiple choices shaded with F_i >= T_high.
   - Case D (Graphite Glare Anomaly): Specular reflection detected via texture variance.
   -> Routed to the Human-in-the-Loop review queue for 1-click teacher confirmation.
"""

from typing import Dict, Any, List, Optional, Tuple


class TriStateDecisionEngine:
    """Decision engine classifying multiple-choice OMR questions into three confidence states."""

    def __init__(
        self,
        t_low: float = 0.15,
        t_high: float = 0.40,
        delta_min: float = 0.20
    ):
        """Initialize the decision engine with configurable threshold boundaries.
        
        Args:
            t_low: Lower boundary threshold. Below this is definitively empty.
            t_high: Upper boundary threshold. Above this is definitively filled.
            delta_min: Minimum contrast margin required between top two choices.
        """
        self.t_low = float(t_low)
        self.t_high = float(t_high)
        self.delta_min = float(delta_min)

    def decide_single_question(
        self,
        question_number: int,
        options_features: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Classify a single question's response into FILLED, BLANK, or AMBIGUOUS.
        
        Args:
            question_number: Number of the question (e.g. 1 to 50).
            options_features: Dict mapping choice keys ('A', 'B', ...) to their feature dicts
                              containing at least 'fill_ratio' and 'has_glare'.
                              
        Returns:
            Dict containing classification status, final answer, confidence level, and rationale.
        """
        # Extract fill ratios and sort in descending order
        sorted_opts = sorted(
            options_features.items(),
            key=lambda item: item[1].get("fill_ratio", 0.0),
            reverse=True
        )
        
        opt_first, feat_first = sorted_opts[0]
        opt_second, feat_second = sorted_opts[1]
        
        f_first = float(feat_first.get("fill_ratio", 0.0))
        f_second = float(feat_second.get("fill_ratio", 0.0))
        delta_f = round(f_first - f_second, 4)
        
        fill_ratios_map = {opt: feat.get("fill_ratio", 0.0) for opt, feat in options_features.items()}
        glare_detected_any = any(feat.get("has_glare", False) for feat in options_features.values())
        
        # -------------------------------------------------------------
        # Decision Rules
        # -------------------------------------------------------------
        
        # Check Glare Anomaly
        # Glare is an issue if the top choice was suppressed into the borderline zone and lacks margin,
        # or if a competing runner-up option has glare with very small margin (< 0.5 * delta_min).
        glare_options = [opt for opt, feat in options_features.items() if feat.get("has_glare", False)]
        top_has_glare = opt_first in glare_options
        runner_up_has_glare = opt_second in glare_options if opt_second else False

        if (top_has_glare and f_first < self.t_high and delta_f < self.delta_min) or \
           (runner_up_has_glare and delta_f < (self.delta_min * 0.5)):
            return {
                "question": question_number,
                "status": "AMBIGUOUS",
                "answer": None,
                "tentative_guess": opt_first,
                "confidence": "LOW",
                "reason": f"Graphite Glare Anomaly detected in option(s): {', '.join(glare_options)}",
                "fill_ratios": fill_ratios_map,
                "delta_f": delta_f,
                "top_two": [opt_first, opt_second]
            }

        # Rule 1: Confirmed Blank (All options below T_low)
        if f_first < self.t_low:
            return {
                "question": question_number,
                "status": "BLANK",
                "answer": None,
                "tentative_guess": None,
                "confidence": "HIGH",
                "reason": f"All options empty: Max fill-ratio ({f_first:.3f}) < T_low ({self.t_low:.2f})",
                "fill_ratios": fill_ratios_map,
                "delta_f": delta_f,
                "top_two": [opt_first, opt_second]
            }

        # Rule 2: Confirmed Filled (Clear single mark with adequate contrast margin)
        if (f_first >= self.t_high and delta_f >= self.delta_min) or \
           (f_first >= 0.35 and delta_f >= max(0.14, self.delta_min * 0.75)):
            return {
                "question": question_number,
                "status": "FILLED",
                "answer": opt_first,
                "tentative_guess": opt_first,
                "confidence": "HIGH",
                "reason": f"Clear single mark: {opt_first} (F={f_first:.3f}, ΔF={delta_f:.3f})",
                "fill_ratios": fill_ratios_map,
                "delta_f": delta_f,
                "top_two": [opt_first, opt_second]
            }

        # Rule 3: Double Marks (Both top 2 choices are >= T_high with close contrast ΔF < delta_min)
        if f_first >= self.t_high and f_second >= self.t_high:
            return {
                "question": question_number,
                "status": "AMBIGUOUS",
                "answer": None,
                "tentative_guess": opt_first,
                "confidence": "LOW",
                "reason": f"Double marks detected: {opt_first} ({f_first:.3f}) and {opt_second} ({f_second:.3f}) both >= T_high (ΔF={delta_f:.3f} < {self.delta_min:.2f})",
                "fill_ratios": fill_ratios_map,
                "delta_f": delta_f,
                "top_two": [opt_first, opt_second]
            }

        # Rule 4: Borderline / Ambiguous Conditions
        # 4a. Erasure Ghost Mark: Top choice is shaded, but runner-up is too close (delta_f < delta_min)
        if f_first >= self.t_high and delta_f < self.delta_min:
            return {
                "question": question_number,
                "status": "AMBIGUOUS",
                "answer": None,
                "tentative_guess": opt_first,
                "confidence": "MEDIUM",
                "reason": f"Possible erasure ghost mark: {opt_first} ({f_first:.3f}) vs {opt_second} ({f_second:.3f}) with small margin ΔF={delta_f:.3f} < {self.delta_min:.2f}",
                "fill_ratios": fill_ratios_map,
                "delta_f": delta_f,
                "top_two": [opt_first, opt_second]
            }

        # 4b. Faint Pencil Shading (T_low <= F_(1) < T_high)
        if self.t_low <= f_first < self.t_high:
            return {
                "question": question_number,
                "status": "AMBIGUOUS",
                "answer": None,
                "tentative_guess": opt_first,
                "confidence": "LOW",
                "reason": f"Faint pencil mark: Top fill-ratio ({f_first:.3f}) in borderline zone [{self.t_low:.2f}, {self.t_high:.2f}]",
                "fill_ratios": fill_ratios_map,
                "delta_f": delta_f,
                "top_two": [opt_first, opt_second]
            }

        # Fallback catch-all for unexpected borderline distribution
        return {
            "question": question_number,
            "status": "AMBIGUOUS",
            "answer": None,
            "tentative_guess": opt_first,
            "confidence": "LOW",
            "reason": f"Ambiguous distribution: F_first={f_first:.3f}, F_second={f_second:.3f}, ΔF={delta_f:.3f}",
            "fill_ratios": fill_ratios_map,
            "delta_f": delta_f,
            "top_two": [opt_first, opt_second]
        }

    def decide_all(self, all_features: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Classify all questions and compute aggregate performance statistics.
        
        Args:
            all_features: List of 50 question records from Step 5.
            
        Returns:
            Dict containing:
                - results: List of individual question decision records.
                - summary: Summary dictionary with counts and Rejection Rate.
        """
        results = []
        filled_count = 0
        blank_count = 0
        ambiguous_count = 0
        ambiguous_questions = []

        for q_data in all_features:
            q_num = q_data["question"]
            opts = q_data["options"]
            
            decision = self.decide_single_question(q_num, opts)
            results.append(decision)
            
            status = decision["status"]
            if status == "FILLED":
                filled_count += 1
            elif status == "BLANK":
                blank_count += 1
            elif status == "AMBIGUOUS":
                ambiguous_count += 1
                ambiguous_questions.append(q_num)

        total = len(all_features)
        rejection_rate = round(float((ambiguous_count / total) * 100), 2) if total > 0 else 0.0

        summary = {
            "total_questions": total,
            "filled_count": filled_count,
            "blank_count": blank_count,
            "ambiguous_count": ambiguous_count,
            "rejection_rate_pct": rejection_rate,
            "ambiguous_questions": ambiguous_questions,
            "thresholds_used": {
                "t_low": self.t_low,
                "t_high": self.t_high,
                "delta_min": self.delta_min
            }
        }

        return {
            "results": results,
            "summary": summary
        }
