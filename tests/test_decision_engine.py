"""Unit Tests for Step 6: Tri-State Decision Engine
Course: ICE415 Digital Image Processing (KMUTT)
"""

import pytest
from omr.decision_engine import TriStateDecisionEngine


@pytest.fixture
def engine():
    return TriStateDecisionEngine(t_low=0.15, t_high=0.40, delta_min=0.20)


def test_decision_confirmed_filled(engine):
    # Option B clearly marked, others nearly empty
    opts = {
        "A": {"fill_ratio": 0.04, "has_glare": False},
        "B": {"fill_ratio": 0.75, "has_glare": False},
        "C": {"fill_ratio": 0.02, "has_glare": False},
        "D": {"fill_ratio": 0.05, "has_glare": False},
        "E": {"fill_ratio": 0.01, "has_glare": False}
    }
    decision = engine.decide_single_question(1, opts)
    assert decision["status"] == "FILLED"
    assert decision["answer"] == "B"
    assert decision["confidence"] == "HIGH"
    assert decision["delta_f"] >= 0.20


def test_decision_confirmed_blank(engine):
    # All options below T_low (0.15)
    opts = {
        "A": {"fill_ratio": 0.02, "has_glare": False},
        "B": {"fill_ratio": 0.04, "has_glare": False},
        "C": {"fill_ratio": 0.03, "has_glare": False},
        "D": {"fill_ratio": 0.01, "has_glare": False},
        "E": {"fill_ratio": 0.02, "has_glare": False}
    }
    decision = engine.decide_single_question(2, opts)
    assert decision["status"] == "BLANK"
    assert decision["answer"] is None
    assert decision["confidence"] == "HIGH"


def test_decision_double_marks(engine):
    # Both B and D are heavily marked
    opts = {
        "A": {"fill_ratio": 0.02, "has_glare": False},
        "B": {"fill_ratio": 0.68, "has_glare": False},
        "C": {"fill_ratio": 0.03, "has_glare": False},
        "D": {"fill_ratio": 0.62, "has_glare": False},
        "E": {"fill_ratio": 0.01, "has_glare": False}
    }
    decision = engine.decide_single_question(3, opts)
    assert decision["status"] == "AMBIGUOUS"
    assert decision["answer"] is None
    assert "Double marks" in decision["reason"]


def test_decision_faint_pencil(engine):
    # Faint mark: highest is 0.28 (between 0.15 and 0.40)
    opts = {
        "A": {"fill_ratio": 0.02, "has_glare": False},
        "B": {"fill_ratio": 0.01, "has_glare": False},
        "C": {"fill_ratio": 0.28, "has_glare": False},
        "D": {"fill_ratio": 0.03, "has_glare": False},
        "E": {"fill_ratio": 0.01, "has_glare": False}
    }
    decision = engine.decide_single_question(4, opts)
    assert decision["status"] == "AMBIGUOUS"
    assert decision["answer"] is None
    assert "Faint pencil" in decision["reason"]


def test_decision_erasure_ghost_mark(engine):
    # Student erased B (residual 0.32) and marked C (0.44), delta = 0.12 < 0.20
    opts = {
        "A": {"fill_ratio": 0.03, "has_glare": False},
        "B": {"fill_ratio": 0.32, "has_glare": False},
        "C": {"fill_ratio": 0.44, "has_glare": False},
        "D": {"fill_ratio": 0.02, "has_glare": False},
        "E": {"fill_ratio": 0.01, "has_glare": False}
    }
    decision = engine.decide_single_question(5, opts)
    assert decision["status"] == "AMBIGUOUS"
    assert decision["answer"] is None
    assert "erasure ghost mark" in decision["reason"].lower()


def test_decision_glare_anomaly(engine):
    # Specular glare flag triggered
    opts = {
        "A": {"fill_ratio": 0.18, "has_glare": True},
        "B": {"fill_ratio": 0.04, "has_glare": False},
        "C": {"fill_ratio": 0.02, "has_glare": False},
        "D": {"fill_ratio": 0.01, "has_glare": False},
        "E": {"fill_ratio": 0.03, "has_glare": False}
    }
    decision = engine.decide_single_question(6, opts)
    assert decision["status"] == "AMBIGUOUS"
    assert "Glare Anomaly" in decision["reason"]


def test_decide_all_aggregation(engine):
    questions_data = [
        # 1: Filled
        {"question": 1, "options": {"A": {"fill_ratio": 0.8}, "B": {"fill_ratio": 0.02}, "C": {"fill_ratio": 0.01}, "D": {"fill_ratio": 0.01}, "E": {"fill_ratio": 0.01}}},
        # 2: Blank
        {"question": 2, "options": {"A": {"fill_ratio": 0.02}, "B": {"fill_ratio": 0.01}, "C": {"fill_ratio": 0.03}, "D": {"fill_ratio": 0.01}, "E": {"fill_ratio": 0.02}}},
        # 3: Ambiguous (faint)
        {"question": 3, "options": {"A": {"fill_ratio": 0.25}, "B": {"fill_ratio": 0.02}, "C": {"fill_ratio": 0.01}, "D": {"fill_ratio": 0.01}, "E": {"fill_ratio": 0.01}}},
        # 4: Filled
        {"question": 4, "options": {"A": {"fill_ratio": 0.01}, "B": {"fill_ratio": 0.01}, "C": {"fill_ratio": 0.02}, "D": {"fill_ratio": 0.72}, "E": {"fill_ratio": 0.01}}}
    ]
    
    summary_res = engine.decide_all(questions_data)
    assert len(summary_res["results"]) == 4
    summary = summary_res["summary"]
    
    assert summary["total_questions"] == 4
    assert summary["filled_count"] == 2
    assert summary["blank_count"] == 1
    assert summary["ambiguous_count"] == 1
    assert summary["rejection_rate_pct"] == 25.0
    assert summary["ambiguous_questions"] == [3]
