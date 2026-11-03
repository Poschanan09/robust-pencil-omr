"""Script to generate interactive Jupyter Notebooks for ICE415 OMR project."""

import json
from pathlib import Path

nb_dir = Path("notebooks")
nb_dir.mkdir(exist_ok=True)

def make_notebook(cells):
    return {
        "cells": cells,
        "metadata": {
            "language_info": {"name": "python", "version": "3.11"},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }

def md_cell(source):
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}

def code_cell(source):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source.splitlines(keepends=True)}

# Notebook 1: Data Exploration
nb1_cells = [
    md_cell("# 🔬 Robust Pencil OMR — Notebook 01: Data Exploration\n\n**Course:** ICE415 Digital Image Processing (KMUTT)\n\nThis notebook demonstrates exploratory data analysis (EDA) on mobile-captured OMR sheets, illustrating real-world imaging challenges:\n- Uneven lighting and diagonal shadow gradients\n- Severe keystoning and perspective distortion\n- Faint pencil shading vs partial erasures\n- Graphite specular reflection (glare)"),
    code_cell("import sys\nsys.path.append('..')\nfrom pathlib import Path\nimport cv2\nimport numpy as np\nimport matplotlib.pyplot as plt\n\nfrom omr.quality_check import assess_quality, check_blur, check_exposure\nfrom omr.grid_extraction import load_template"),
    md_cell("## 1. Inspect A4 Answer Sheet Template & Specifications"),
    code_cell("template = load_template()\nprint(f\"Template Name: {template.get('template_name')}\")\nprint(f\"Questions: {template.get('questions_count')} | Options per Q: {template.get('options_per_question')}\")\nprint(f\"Bounding Frame: {template.get('bounding_frame')}\")"),
    md_cell("## 2. Quality Assessment on Sample Captures"),
    code_cell("img_path = Path('../templates/answer_sheet_a4.png')\nif img_path.exists():\n    img = cv2.imread(str(img_path))\n    res = assess_quality(img)\n    print('Quality Assessment Summary:', res)\nelse:\n    print('Template PNG not found at path.')"),
    md_cell("## 3. Histogram Analysis: Shadowed vs Uniform Lighting"),
    code_cell("canvas = np.ones((600, 400), dtype=np.uint8) * 240\ngradient = np.tile(np.linspace(0, 160, 400), (600, 1)).astype(np.uint8)\nshadowed = cv2.subtract(canvas, gradient)\n\nfig, axes = plt.subplots(1, 2, figsize=(12, 4))\naxes[0].imshow(canvas, cmap='gray', vmin=0, vmax=255)\naxes[0].set_title('Uniform Canvas')\naxes[1].imshow(shadowed, cmap='gray', vmin=0, vmax=255)\naxes[1].set_title('Shadowed Capture')\nplt.tight_layout()\nplt.show()")
]

with open(nb_dir / "01_data_exploration.ipynb", "w", encoding="utf-8") as f:
    json.dump(make_notebook(nb1_cells), f, indent=2)

# Notebook 2: Pipeline Demo
nb2_cells = [
    md_cell("# 🚀 Robust Pencil OMR — Notebook 02: End-to-End Pipeline Walkthrough\n\n**Course:** ICE415 Digital Image Processing (KMUTT)\n\nInteractive step-by-step execution of the 7-step classical DIP pipeline:\n1. Input Quality Check (Laplacian Blur & Histogram Exposure)\n2. Document Boundary Detection (Canny + Douglas-Peucker)\n3. Homography Perspective Rectification (Projective 4-Point Warp)\n4. Local Adaptive Gaussian Thresholding + Mathematical Morphology\n5. Inner-Ring Masking & Feature Extraction\n6. Tri-State Decision Logic (FILLED, BLANK, AMBIGUOUS)\n7. Diagnostic Overlay Rendering"),
    code_cell("import sys\nsys.path.append('..')\nfrom pathlib import Path\nimport cv2\nimport numpy as np\nimport matplotlib.pyplot as plt\n\nfrom omr.pipeline import OMRPipeline\nfrom omr.decision_engine import TriStateDecisionEngine"),
    md_cell("## 1. Initialize OMR Pipeline"),
    code_cell("pipeline = OMRPipeline()\nprint('Pipeline successfully initialized with canonical DPI 300!')"),
    md_cell("## 2. Run Pipeline on Template Sample"),
    code_cell("sample_path = Path('../templates/answer_sheet_a4.png')\nif sample_path.exists():\n    results = pipeline.process_single_image(sample_path)\n    print(f\"Processed Status: {results['status']}\")\n    print('Summary:', results['summary'])\nelse:\n    print('Please provide an answer sheet image to test.')"),
    md_cell("## 3. Visualize Intermediate Pipeline Stages"),
    code_cell("if sample_path.exists() and 'debug_images' in results:\n    debugs = results['debug_images']\n    fig, axes = plt.subplots(1, 3, figsize=(18, 6))\n    if 'canny_edges' in debugs:\n        axes[0].imshow(debugs['canny_edges'], cmap='gray')\n        axes[0].set_title('Step 2: Canny Edges')\n    if 'binary_clean' in debugs:\n        axes[1].imshow(debugs['binary_clean'], cmap='gray')\n        axes[1].set_title('Step 4: Binary Clean')\n    if 'overlay' in debugs:\n        axes[2].imshow(cv2.cvtColor(debugs['overlay'], cv2.COLOR_BGR2RGB))\n        axes[2].set_title('Step 7: Diagnostic Overlay')\n    plt.tight_layout()\n    plt.show()")
]

with open(nb_dir / "02_pipeline_demo.ipynb", "w", encoding="utf-8") as f:
    json.dump(make_notebook(nb2_cells), f, indent=2)

print("Successfully created Jupyter Notebooks in notebooks/")
