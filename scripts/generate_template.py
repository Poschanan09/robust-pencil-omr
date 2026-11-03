"""OMR Answer Sheet & Template Configuration Generator
Course: ICE415 Digital Image Processing (KMUTT)

Generates:
1. templates/answer_sheet_a4.pdf (Printable high-precision vector A4 sheet)
2. templates/answer_sheet_a4.png (300 DPI 2480x3508 canonical image)
3. templates/template_config.json (Normalized percentage coordinates of all 250 bubbles)
"""

import json
from pathlib import Path
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# A4 Dimensions in millimeters
PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0

# 300 DPI Standard Dimensions in Pixels
CANVAS_WIDTH_PX = 2480
CANVAS_HEIGHT_PX = 3508

def build_template_coordinates():
    """Compute exact millimeter, pixel, and normalized coordinates for all elements."""
    # Outer frame
    frame_x = 10.0
    frame_y = 10.0
    frame_w = 190.0
    frame_h = 277.0

    # 4 Corner Fiducial Markers (12mm x 12mm solid squares)
    marker_size = 12.0
    margin = 3.0
    markers = {
        "top_left": {
            "x": frame_x + margin,
            "y": frame_y + margin,
            "w": marker_size,
            "h": marker_size
        },
        "top_right": {
            "x": frame_x + frame_w - margin - marker_size,
            "y": frame_y + margin,
            "w": marker_size,
            "h": marker_size
        },
        "bottom_left": {
            "x": frame_x + margin,
            "y": frame_y + frame_h - margin - marker_size,
            "w": marker_size,
            "h": marker_size
        },
        "bottom_right": {
            "x": frame_x + frame_w - margin - marker_size,
            "y": frame_y + frame_h - margin - marker_size,
            "w": marker_size,
            "h": marker_size
        }
    }

    # Questions layout
    # 50 Questions: Col 1 = Q1-25, Col 2 = Q26-50
    start_y = 66.0
    row_height = 8.1
    bubble_radius_mm = 3.2

    col1_q_x = 30.0
    col1_opts_x = {"A": 43.0, "B": 53.0, "C": 63.0, "D": 73.0, "E": 83.0}

    col2_q_x = 124.0
    col2_opts_x = {"A": 137.0, "B": 147.0, "C": 157.0, "D": 167.0, "E": 177.0}

    questions_data = []

    for q_idx in range(1, 51):
        if q_idx <= 25:
            # Column 1
            row = q_idx - 1
            cy = start_y + (row * row_height)
            q_x = col1_q_x
            opts_map = col1_opts_x
        else:
            # Column 2
            row = q_idx - 26
            cy = start_y + (row * row_height)
            q_x = col2_q_x
            opts_map = col2_opts_x

        options = {}
        for opt, cx in opts_map.items():
            # Normalized [0.0 - 1.0] relative to the detected bounding frame
            cx_pct = round((cx - frame_x) / frame_w, 5)
            cy_pct = round((cy - frame_y) / frame_h, 5)
            r_pct = round(bubble_radius_mm / frame_w, 5)

            options[opt] = {
                # Millimeters
                "cx_mm": round(cx, 2),
                "cy_mm": round(cy, 2),
                "r_mm": round(bubble_radius_mm, 2),
                # Normalized [0.0 - 1.0] relative to bounding frame
                "cx_pct": cx_pct,
                "cy_pct": cy_pct,
                "r_pct": r_pct,
                # Pixel coordinates on canonical canvas
                "cx_px": int(round(cx_pct * CANVAS_WIDTH_PX)),
                "cy_px": int(round(cy_pct * CANVAS_HEIGHT_PX)),
                "r_px": int(round(r_pct * CANVAS_WIDTH_PX))
            }

        questions_data.append({
            "q": q_idx,
            "q_x_mm": round(q_x, 2),
            "q_y_mm": round(cy, 2),
            "options": options
        })

    config = {
        "template_name": "ICE415_Standard_A4_50Q_5Opts",
        "version": "1.0.0",
        "paper_size": "A4",
        "canvas_size": {
            "width_mm": PAGE_WIDTH_MM,
            "height_mm": PAGE_HEIGHT_MM,
            "width_px_300dpi": CANVAS_WIDTH_PX,
            "height_px_300dpi": CANVAS_HEIGHT_PX
        },
        "bounding_frame": {
            "x_mm": frame_x,
            "y_mm": frame_y,
            "w_mm": frame_w,
            "h_mm": frame_h,
            "x_pct": round(frame_x / PAGE_WIDTH_MM, 5),
            "y_pct": round(frame_y / PAGE_HEIGHT_MM, 5),
            "w_pct": round(frame_w / PAGE_WIDTH_MM, 5),
            "h_pct": round(frame_h / PAGE_HEIGHT_MM, 5)
        },
        "fiducial_markers": markers,
        "inner_mask_radius_ratio": 0.82,
        "questions_count": 50,
        "options_per_question": 5,
        "options_labels": ["A", "B", "C", "D", "E"],
        "questions": questions_data
    }

    return config

def generate_pdf(config: dict, output_path: Path):
    """Generate high-precision vector PDF using fpdf2."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.set_draw_color(0, 0, 0)

    # 1. Outer Frame (1.2mm stroke)
    pdf.set_line_width(1.2)
    bf = config["bounding_frame"]
    pdf.rect(bf["x_mm"], bf["y_mm"], bf["w_mm"], bf["h_mm"])

    # 2. Fiducial Markers (solid black squares)
    pdf.set_fill_color(0, 0, 0)
    for m in config["fiducial_markers"].values():
        pdf.rect(m["x"], m["y"], m["w"], m["h"], style="F")

    # 3. Header Information
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_xy(30, 13)
    pdf.cell(150, 6, "KING MONGKUT'S UNIVERSITY OF TECHNOLOGY THONBURI", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 10.5)
    pdf.set_xy(30, 20)
    pdf.cell(150, 5, "ICE415 Digital Image Processing - OMR Answer Sheet", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_xy(30, 26)
    pdf.cell(150, 4, "Form: 50 Questions | 5 Options (A, B, C, D, E) | Pencil 2B Only", align="C")

    # 4. Student Metadata Boxes
    pdf.set_line_width(0.3)
    # Student ID Box
    pdf.rect(32, 33, 70, 16)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(33, 34)
    pdf.cell(68, 4, "STUDENT ID (11 DIGITS):", align="L")
    # Draw 11 individual digit boxes
    box_w = 5.5
    for i in range(11):
        pdf.rect(34 + (i * 6.1), 39, box_w, 8)

    # Student Name Box
    pdf.rect(108, 33, 70, 16)
    pdf.set_xy(109, 34)
    pdf.cell(68, 4, "STUDENT NAME & SURNAME:", align="L")
    pdf.set_line_width(0.2)
    pdf.line(110, 46, 175, 46)

    # 5. Instructions & Exam Policy Bar
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(30, 52, 150, 7, style="FD")
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(40, 40, 40)
    pdf.set_xy(30, 53.5)
    pdf.cell(150, 4, "Instructions: Fill the oval completely with 2B pencil. Erase cleanly if changing. Do not fold or smudge.", align="C")
    pdf.set_text_color(0, 0, 0)

    # 6. Column Divider Line
    pdf.set_line_width(0.4)
    pdf.line(105, 63, 105, 271)

    # 7. Column Header Labels
    pdf.set_font("Helvetica", "B", 8)
    # Column 1 header
    pdf.set_xy(30, 61.5)
    pdf.cell(8, 4, "NO.", align="C")
    for opt, x in [("A", 43.0), ("B", 53.0), ("C", 63.0), ("D", 73.0), ("E", 83.0)]:
        pdf.set_xy(x - 3.2, 61.5)
        pdf.cell(6.4, 4, opt, align="C")

    # Column 2 header
    pdf.set_xy(124, 61.5)
    pdf.cell(8, 4, "NO.", align="C")
    for opt, x in [("A", 137.0), ("B", 147.0), ("C", 157.0), ("D", 167.0), ("E", 177.0)]:
        pdf.set_xy(x - 3.2, 61.5)
        pdf.cell(6.4, 4, opt, align="C")

    # 8. Questions and Bubbles
    r = config["questions"][0]["options"]["A"]["r_mm"]
    pdf.set_line_width(0.35)

    for q in config["questions"]:
        # Question Number
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_xy(q["q_x_mm"] - 4.0, q["q_y_mm"] - 2.5)
        pdf.cell(8, 5, f"{q['q']:02d}", align="R")

        # Bubbles
        for opt, opt_data in q["options"].items():
            cx = opt_data["cx_mm"]
            cy = opt_data["cy_mm"]
            # Draw circle outline
            pdf.ellipse(cx - r, cy - r, 2 * r, 2 * r, style="D")
            # Draw option letter inside
            pdf.set_font("Helvetica", "", 7)
            pdf.set_xy(cx - r, cy - 2.0)
            pdf.cell(2 * r, 4, opt, align="C")

    # 9. Bottom Footer
    pdf.set_font("Helvetica", "I", 6.5)
    pdf.set_xy(30, 273)
    pdf.cell(150, 4, "KMUTT Computer Engineering | ICE415 Robust Pencil OMR Project | Form Ref: ICE415-OMR-A4", align="C")

    pdf.output(str(output_path))
    print(f"✅ Generated PDF Answer Sheet: {output_path}")

def generate_png_canvas(config: dict, output_path: Path):
    """Generate high-resolution 300 DPI image (2480x3508) using Pillow."""
    img = Image.new("RGB", (CANVAS_WIDTH_PX, CANVAS_HEIGHT_PX), color="white")
    draw = ImageDraw.Draw(img)

    def mm_to_px(mm_val, is_width=True):
        ratio = mm_val / (PAGE_WIDTH_MM if is_width else PAGE_HEIGHT_MM)
        dim = CANVAS_WIDTH_PX if is_width else CANVAS_HEIGHT_PX
        return int(round(ratio * dim))

    # Outer Frame (thick border: ~14px)
    bf = config["bounding_frame"]
    x0 = mm_to_px(bf["x_mm"], True)
    y0 = mm_to_px(bf["y_mm"], False)
    x1 = mm_to_px(bf["x_mm"] + bf["w_mm"], True)
    y1 = mm_to_px(bf["y_mm"] + bf["h_mm"], False)
    draw.rectangle([x0, y0, x1, y1], outline="black", width=14)

    # 4 Corner Fiducial Markers (solid black squares)
    for m in config["fiducial_markers"].values():
        mx0 = mm_to_px(m["x"], True)
        my0 = mm_to_px(m["y"], False)
        mx1 = mm_to_px(m["x"] + m["w"], True)
        my1 = mm_to_px(m["y"] + m["h"], False)
        draw.rectangle([mx0, my0, mx1, my1], fill="black")

    # Header Texts
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 46)
        font_sub = ImageFont.truetype("arialbd.ttf", 36)
        font_inst = ImageFont.truetype("arial.ttf", 26)
        font_q = ImageFont.truetype("arialbd.ttf", 28)
        font_opt = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 22)
    except:
        font_title = ImageFont.load_default()
        font_sub = font_title
        font_inst = font_title
        font_q = font_title
        font_opt = font_title
        font_small = font_title

    # Header
    draw.text((CANVAS_WIDTH_PX // 2, mm_to_px(16, False)), "KING MONGKUT'S UNIVERSITY OF TECHNOLOGY THONBURI", fill="black", font=font_title, anchor="mm")
    draw.text((CANVAS_WIDTH_PX // 2, mm_to_px(22.5, False)), "ICE415 Digital Image Processing - OMR Answer Sheet", fill="black", font=font_sub, anchor="mm")
    draw.text((CANVAS_WIDTH_PX // 2, mm_to_px(28, False)), "Form: 50 Questions | 5 Options (A, B, C, D, E) | Pencil 2B Only", fill="black", font=font_small, anchor="mm")

    # Student metadata boxes
    id_x0, id_y0 = mm_to_px(32, True), mm_to_px(33, False)
    id_x1, id_y1 = mm_to_px(102, True), mm_to_px(49, False)
    draw.rectangle([id_x0, id_y0, id_x1, id_y1], outline="black", width=3)
    draw.text((id_x0 + 15, id_y0 + 15), "STUDENT ID (11 DIGITS):", fill="black", font=font_small)
    for i in range(11):
        bx0 = mm_to_px(34 + (i * 6.1), True)
        by0 = mm_to_px(39, False)
        bx1 = bx0 + mm_to_px(5.5, True)
        by1 = by0 + mm_to_px(8, False)
        draw.rectangle([bx0, by0, bx1, by1], outline="black", width=2)

    nm_x0, nm_y0 = mm_to_px(108, True), mm_to_px(33, False)
    nm_x1, nm_y1 = mm_to_px(178, True), mm_to_px(49, False)
    draw.rectangle([nm_x0, nm_y0, nm_x1, nm_y1], outline="black", width=3)
    draw.text((nm_x0 + 15, nm_y0 + 15), "STUDENT NAME & SURNAME:", fill="black", font=font_small)
    draw.line([nm_x0 + 15, nm_y1 - 25, nm_x1 - 15, nm_y1 - 25], fill="black", width=2)

    # Instructions Banner
    ib_x0, ib_y0 = mm_to_px(30, True), mm_to_px(52, False)
    ib_x1, ib_y1 = mm_to_px(180, True), mm_to_px(59, False)
    draw.rectangle([ib_x0, ib_y0, ib_x1, ib_y1], fill="#eeeeee", outline="black", width=2)
    draw.text((CANVAS_WIDTH_PX // 2, (ib_y0 + ib_y1) // 2), "Instructions: Fill the oval completely with 2B pencil. Erase cleanly if changing.", fill="black", font=font_inst, anchor="mm")

    # Column divider line
    div_x = mm_to_px(105, True)
    draw.line([div_x, mm_to_px(63, False), div_x, mm_to_px(271, False)], fill="black", width=4)

    # Headers for columns
    draw.text((mm_to_px(30, True), mm_to_px(63.5, False)), "NO.", fill="black", font=font_q, anchor="mm")
    for opt, cx_mm in [("A", 43.0), ("B", 53.0), ("C", 63.0), ("D", 73.0), ("E", 83.0)]:
        draw.text((mm_to_px(cx_mm, True), mm_to_px(63.5, False)), opt, fill="black", font=font_q, anchor="mm")

    draw.text((mm_to_px(124, True), mm_to_px(63.5, False)), "NO.", fill="black", font=font_q, anchor="mm")
    for opt, cx_mm in [("A", 137.0), ("B", 147.0), ("C", 157.0), ("D", 167.0), ("E", 177.0)]:
        draw.text((mm_to_px(cx_mm, True), mm_to_px(63.5, False)), opt, fill="black", font=font_q, anchor="mm")

    # Questions & Bubbles
    for q in config["questions"]:
        # Question label
        qx_px = mm_to_px(q["q_x_mm"], True)
        qy_px = mm_to_px(q["q_y_mm"], False)
        draw.text((qx_px, qy_px), f"{q['q']:02d}", fill="black", font=font_q, anchor="mm")

        for opt, opt_data in q["options"].items():
            cx_px = opt_data["cx_px"]
            cy_px = opt_data["cy_px"]
            r_px = opt_data["r_px"]

            # Circle outline (stroke ~4px)
            draw.ellipse([cx_px - r_px, cy_px - r_px, cx_px + r_px, cy_px + r_px], outline="black", width=4)
            # Centered option text
            draw.text((cx_px, cy_px), opt, fill="black", font=font_opt, anchor="mm")

    # Footer
    draw.text((CANVAS_WIDTH_PX // 2, mm_to_px(275, False)), "KMUTT Computer Engineering | ICE415 Robust Pencil OMR Project | Form Ref: ICE415-OMR-A4", fill="#555555", font=font_small, anchor="mm")

    img.save(output_path, dpi=(300, 300))
    print(f"✅ Generated 300 DPI PNG Canvas: {output_path}")

def main():
    print("==================================================")
    print("📄 ICE415 Robust Pencil OMR - Template Generator")
    print("==================================================")

    config = build_template_coordinates()

    # 1. Save JSON config
    json_path = TEMPLATES_DIR / "template_config.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"✅ Generated Coordinates JSON: {json_path}")
    print(f"   Total Questions: {config['questions_count']}")
    print(f"   Total Bubble Points: {config['questions_count'] * config['options_per_question']}")

    # 2. Save PDF
    pdf_path = TEMPLATES_DIR / "answer_sheet_a4.pdf"
    generate_pdf(config, pdf_path)

    # 3. Save 300 DPI Canvas PNG
    png_path = TEMPLATES_DIR / "answer_sheet_a4.png"
    generate_png_canvas(config, png_path)

    print("==================================================")
    print("🎉 Phase 2 Complete: Templates ready!")
    print("==================================================")

if __name__ == "__main__":
    main()
