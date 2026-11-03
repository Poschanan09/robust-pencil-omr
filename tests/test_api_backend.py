"""Integration & API Tests for FastAPI Backend (Phase 10)
Course: ICE415 Digital Image Processing (KMUTT)
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_IMAGE = BASE_DIR / "templates" / "answer_sheet_a4.png"

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "KMUTT" in data["course"]


def test_api_upload_flow():
    assert TEMPLATE_IMAGE.exists()
    
    with open(TEMPLATE_IMAGE, "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("test_sheet.png", f, "image/png")}
        )
        
    assert response.status_code == 201
    data = response.json()
    assert "image_id" in data
    assert data["status"] == "uploaded"
    assert data["filename"] == "test_sheet.png"
    
    image_id = data["image_id"]
    
    # 2. Process image
    proc_res = client.post(f"/api/process/{image_id}")
    assert proc_res.status_code == 200
    pdata = proc_res.json()
    assert pdata["image_id"] == image_id
    assert pdata["status"] == "success"
    assert "summary" in pdata
    
    # 3. Check review queue
    review_res = client.get(f"/api/review/{image_id}/queue")
    assert review_res.status_code == 200
    rdata = review_res.json()
    assert "queue" in rdata
    
    # 4. Human Decision override test (e.g. override question 1 to 'A')
    decide_res = client.post(
        f"/api/review/{image_id}/decide",
        json={"question": 1, "decision": "A"}
    )
    assert decide_res.status_code == 200
    ddata = decide_res.json()
    assert ddata["question"] == 1
    assert ddata["decision"] == "A"
    assert ddata["status"] == "updated"
    
    # 5. Get Result detail
    res_detail = client.get(f"/api/results/{image_id}")
    assert res_detail.status_code == 200
    res_data = res_detail.json()
    assert res_data["image_id"] == image_id
    assert res_data["results"][0]["answer"] == "A"
    
    # 6. Score against an Answer Key
    score_res = client.post(
        f"/api/results/{image_id}/score",
        json={"answer_key": {"1": "A", "2": "B"}}
    )
    assert score_res.status_code == 200
    s_data = score_res.json()
    assert s_data["correct_count"] >= 1
    
    # 7. Export CSV
    export_res = client.get(f"/api/results/{image_id}/export/csv")
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers["content-type"]
    assert "image_id,question,status,answer" in export_res.text
