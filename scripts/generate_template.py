"""OMR Answer Sheet & Template Configuration Generator
Course: ICE415 Digital Image Processing (KMUTT)

Generates:
1. templates/answer_sheet_a4.pdf (Printable vector A4 sheet with 2x A5 sets of 40Q)
2. templates/answer_sheet_a4.png (300 DPI 2480x3508 canonical image)
3. templates/template_config.json (Normalized percentage coordinates of bubbles and markers)
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
MID_Y_MM = 148.5  # Exact horizontal center dividing A4 into two A5 sheets

# 300 DPI Standard Dimensions in Pixels
CANVAS_WIDTH_PX = 2480
CANVAS_HEIGHT_PX = 3508

def build_template_coordinates():
    """Compute exact millimeter, pixel, and normalized coordinates for 2x A5 sheets on A4."""
    bubble_radius_mm = 3.0  # Diameter = 6.0 mm
    row_height_mm = 7.8     # Vertical pitch = 7.8 mm
    bubble_pitch_x = 8.0    # Center-to-center pitch between A, B, C, D, E

    # Unified Outer Bounding Frame across the A4 page
    frame_x = 7.0
    frame_y = 6.0
    frame_w = 196.0
    frame_h = 285.0

    # 4 Corner Fiducial Markers (9.0mm x 9.0mm solid black squares)
    m_size = 9.0
    margin = 2.5
    markers = {
        "top_left": {"x": frame_x + margin, "y": frame_y + margin, "w": m_size, "h": m_size},
        "top_right": {"x": frame_x + frame_w - margin - m_size, "y": frame_y + margin, "w": m_size, "h": m_size},
        "bottom_left": {"x": frame_x + margin, "y": frame_y + frame_h - margin - m_size, "w": m_size, "h": m_size},
        "bottom_right": {"x": frame_x + frame_w - margin - m_size, "y": frame_y + frame_h - margin - m_size, "w": m_size, "h": m_size}
    }

    # 4 Columns of 10 Questions
    # Col 1: Q01-Q10, Col 2: Q11-Q20, Col 3: Q21-Q30, Col 4: Q31-Q40
    cols_config = [
        {"col": 1, "q_start": 1,  "q_end": 10, "q_x": 13.0, "a_x": 19.0},
        {"col": 2, "q_start": 11, "q_end": 20, "q_x": 61.5, "a_x": 67.5},
        {"col": 3, "q_start": 21, "q_end": 30, "q_x": 110.0, "a_x": 116.0},
        {"col": 4, "q_start": 31, "q_end": 40, "q_x": 158.5, "a_x": 164.5},
    ]

    sheets = []
    # Sheet 1: Top half (y0 = 6.0 mm)
    # Sheet 2: Bottom half (y0 = 154.5 mm)
    sheet_offsets = [
        {"sheet_id": 1, "name": "Sheet 1 (Top A5)", "y0": 6.0},
        {"sheet_id": 2, "name": "Sheet 2 (Bottom A5)", "y0": 154.5}
    ]

    for s_info in sheet_offsets:
        s_id = s_info["sheet_id"]
        y0 = s_info["y0"]
        start_y = y0 + 44.0

        sheet_questions = []

        for col_data in cols_config:
            q_start = col_data["q_start"]
            q_end = col_data["q_end"]
            q_x = col_data["q_x"]
            a_x = col_data["a_x"]

            for row_idx, q_num in enumerate(range(q_start, q_end + 1)):
                cy = start_y + (row_idx * row_height_mm)

                options = {}
                for opt_idx, opt_label in enumerate(["A", "B", "C", "D", "E"]):
                    cx = a_x + (opt_idx * bubble_pitch_x)

                    # Normalized coordinates relative to the detected outer frame
                    cx_pct = round((cx - frame_x) / frame_w, 5)
                    cy_pct = round((cy - frame_y) / frame_h, 5)
                    r_pct = round(bubble_radius_mm / frame_w, 5)

                    options[opt_label] = {
                        "cx_mm": round(cx, 2),
                        "cy_mm": round(cy, 2),
                        "r_mm": round(bubble_radius_mm, 2),
                        "cx_pct": cx_pct,
                        "cy_pct": cy_pct,
                        "r_pct": r_pct,
                        "cx_px": int(round(cx_pct * CANVAS_WIDTH_PX)),
                        "cy_px": int(round(cy_pct * CANVAS_HEIGHT_PX)),
                        "r_px": int(round(r_pct * CANVAS_WIDTH_PX))
                    }

                q_entry = {
                    "sheet": s_id,
                    "q": q_num,
                    "q_x_mm": round(q_x, 2),
                    "q_y_mm": round(cy, 2),
                    "options": options
                }
                sheet_questions.append(q_entry)

        sheets.append({
            "sheet_id": s_id,
            "y0_mm": y0,
            "questions": sheet_questions
        })

    config = {
        "template_name": "ICE415_Dual_A5_40Q_5Opts",
        "version": "2.0.0",
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
        "cut_line_y_mm": MID_Y_MM,
        "sheets_count": 2,
        "questions_per_sheet": 40,
        "questions_count": 40,
        "options_per_question": 5,
        "options_labels": ["A", "B", "C", "D", "E"],
        "bubble_diameter_mm": 6.0,
        "bubble_radius_mm": bubble_radius_mm,
        "bubble_pitch_x_mm": bubble_pitch_x,
        "row_height_y_mm": row_height_mm,
        "inner_mask_radius_ratio": 0.82,
        "sheets": sheets,
        # Default questions list is Sheet 1 (Top A5 sheet)
        "questions": sheets[0]["questions"],
        "sheet2_questions": sheets[1]["questions"]
    }

    return config

def generate_pdf(config: dict, output_path: Path):
    """Generate high-precision vector A4 PDF containing 2x A5 answer sheets with cutting guide."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.set_draw_color(0, 0, 0)

    # 1. Outer A4 Frame (1.0 mm stroke)
    bf = config["bounding_frame"]
    pdf.set_line_width(1.0)
    pdf.rect(bf["x_mm"], bf["y_mm"], bf["w_mm"], bf["h_mm"])

    # 2. 4 Corner Fiducial Markers (solid black squares)
    pdf.set_fill_color(0, 0, 0)
    for m in config["fiducial_markers"].values():
        pdf.rect(m["x"], m["y"], m["w"], m["h"], style="F")

    # 3. Middle Horizontal Cut Line (dashed at 148.5 mm)
    cut_y = config["cut_line_y_mm"]
    pdf.set_line_width(0.35)
    pdf.set_dash_pattern(dash=2.5, gap=1.5)
    pdf.line(bf["x_mm"], cut_y, bf["x_mm"] + bf["w_mm"], cut_y)
    pdf.set_dash_pattern()

    # Cut guide label badge in the center
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_fill_color(255, 255, 255)
    cut_label = "  -- [ CUT HERE : SEPARATE INTO 2 A5 ANSWER SHEETS ] --  "
    lbl_w = pdf.get_string_width(cut_label) + 4
    pdf.set_xy((PAGE_WIDTH_MM - lbl_w) / 2, cut_y - 2.0)
    pdf.cell(lbl_w, 4, cut_label, align="C", fill=True)

    # 4. Render both A5 sheets (Sheet 1 = top, Sheet 2 = bottom)
    cols_headers = [
        {"qx": 13.0, "ax": 19.0},
        {"qx": 61.5, "ax": 67.5},
        {"qx": 110.0, "ax": 116.0},
        {"qx": 158.5, "ax": 164.5}
    ]
    r = config["bubble_radius_mm"]

    for s_data in config["sheets"]:
        s_id = s_data["sheet_id"]
        y0 = s_data["y0_mm"]

        # Header Titles
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_xy(25, y0 + 2.5)
        pdf.cell(160, 4.5, "KING MONGKUT'S UNIVERSITY OF TECHNOLOGY THONBURI", align="C")

        pdf.set_font("Helvetica", "B", 8.0)
        pdf.set_xy(25, y0 + 6.6)
        pdf.cell(160, 4.0, "ICE415 Digital Image Processing - OMR Answer Sheet", align="C")

        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_xy(25, y0 + 10.3)
        pdf.cell(160, 3.5, f"Form: 40 Questions | 5 Options (A-E) | Pencil 2B Only | Sheet {s_id} [A5]", align="C")

        # Student Metadata Boxes
        pdf.set_line_width(0.3)
        # Left Box: Student ID (11 Digits)
        box_top_y = y0 + 14.5
        box_h = 14.0
        pdf.rect(21.0, box_top_y, 78.0, box_h)
        pdf.set_font("Helvetica", "B", 7.0)
        pdf.set_xy(22.5, box_top_y + 1.2)
        pdf.cell(75.0, 3.5, "STUDENT ID (11 DIGITS):", align="L")

        digit_box_w = 6.0
        digit_box_h = 7.0
        digit_pitch = 6.7
        for d_i in range(11):
            dbx = 22.5 + (d_i * digit_pitch)
            dby = box_top_y + 5.2
            pdf.rect(dbx, dby, digit_box_w, digit_box_h)

        # Right Box: Student Name, Subject, Class/Section
        pdf.rect(103.0, box_top_y, 86.0, box_h)
        pdf.set_xy(104.5, box_top_y + 1.2)
        pdf.cell(32.0, 3.5, "NAME - SURNAME:", align="L")
        pdf.set_line_width(0.2)
        pdf.line(136.0, box_top_y + 4.5, 187.0, box_top_y + 4.5)

        pdf.set_line_width(0.3)
        pdf.set_xy(104.5, box_top_y + 8.2)
        pdf.cell(16.0, 3.5, "SUBJECT:", align="L")
        pdf.set_line_width(0.2)
        pdf.line(120.0, box_top_y + 11.5, 154.0, box_top_y + 11.5)

        pdf.set_line_width(0.3)
        pdf.set_xy(156.0, box_top_y + 8.2)
        pdf.cell(14.0, 3.5, "SEC / RM:", align="L")
        pdf.set_line_width(0.2)
        pdf.line(170.0, box_top_y + 11.5, 187.0, box_top_y + 11.5)

        # Instructions Bar
        pdf.set_fill_color(240, 240, 240)
        pdf.set_line_width(0.25)
        pdf.rect(21.0, y0 + 30.5, 168.0, 4.8, style="FD")
        pdf.set_font("Helvetica", "I", 6.5)
        pdf.set_text_color(40, 40, 40)
        pdf.set_xy(21.0, y0 + 31.2)
        pdf.cell(168.0, 3.5, "Instructions: Fill the oval completely with 2B pencil. Erase cleanly if changing. Do not fold or smudge.", align="C")
        pdf.set_text_color(0, 0, 0)

        # Column Dividers (3 vertical lines between the 4 columns)
        pdf.set_line_width(0.35)
        dividers_x = [56.5, 105.0, 153.5]
        for div_x in dividers_x:
            pdf.line(div_x, y0 + 36.5, div_x, y0 + 122.5)

        # Column Header Labels (NO. A B C D E)
        pdf.set_font("Helvetica", "B", 7.0)
        hdr_y = y0 + 37.0
        for col_hdr in cols_headers:
            pdf.set_xy(col_hdr["qx"] - 3.5, hdr_y)
            pdf.cell(7.0, 3.5, "NO.", align="C")
            for o_i, o_label in enumerate(["A", "B", "C", "D", "E"]):
                ox = col_hdr["ax"] + (o_i * config["bubble_pitch_x_mm"])
                pdf.set_xy(ox - r, hdr_y)
                pdf.cell(2 * r, 3.5, o_label, align="C")

        # Questions and Bubbles (40 Questions)
        pdf.set_line_width(0.3)
        for q in s_data["questions"]:
            # Question number in bold
            pdf.set_font("Helvetica", "B", 7.0)
            pdf.set_xy(q["q_x_mm"] - 4.0, q["q_y_mm"] - 1.8)
            pdf.cell(7.0, 3.6, f"{q['q']:02d}", align="R")

            # 5 Bubbles
            for opt_key, opt_data in q["options"].items():
                cx = opt_data["cx_mm"]
                cy = opt_data["cy_mm"]

                # Circle outline
                pdf.ellipse(cx - r, cy - r, 2 * r, 2 * r, style="D")

                # Option letter inside bubble
                pdf.set_font("Helvetica", "", 5.5)
                pdf.set_text_color(90, 90, 90)
                pdf.set_xy(cx - r, cy - 1.5)
                pdf.cell(2 * r, 3.0, opt_key, align="C")
                pdf.set_text_color(0, 0, 0)

        # Footer of each sheet
        pdf.set_font("Helvetica", "I", 6.0)
        pdf.set_xy(25.0, y0 + 125.5)
        pdf.cell(160.0, 3.5, f"KMUTT Computer Engineering | ICE415 Robust Pencil OMR Project | Form: A5-40Q-Sheet{s_id}", align="C")

    pdf.output(str(output_path))
    print(f"✅ Generated Vector PDF Answer Sheet: {output_path}")

def generate_png_canvas(config: dict, output_path: Path):
    """Generate high-resolution 300 DPI image (2480x3508) using Pillow."""
    img = Image.new("RGB", (CANVAS_WIDTH_PX, CANVAS_HEIGHT_PX), color="white")
    draw = ImageDraw.Draw(img)

    def mm_to_px(mm_val, is_width=True):
        ratio = mm_val / (PAGE_WIDTH_MM if is_width else PAGE_HEIGHT_MM)
        dim = CANVAS_WIDTH_PX if is_width else CANVAS_HEIGHT_PX
        return int(round(ratio * dim))

    # Font handling
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 34)
        font_sub = ImageFont.truetype("arialbd.ttf", 26)
        font_small = ImageFont.truetype("arial.ttf", 20)
        font_bold = ImageFont.truetype("arialbd.ttf", 22)
        font_q = ImageFont.truetype("arialbd.ttf", 22)
        font_opt = ImageFont.truetype("arial.ttf", 18)
    except:
        font_title = ImageFont.load_default()
        font_sub = font_title
        font_small = font_title
        font_bold = font_title
        font_q = font_title
        font_opt = font_title

    # 1. Outer A4 Frame
    bf = config["bounding_frame"]
    x0_px = mm_to_px(bf["x_mm"], True)
    y0_px = mm_to_px(bf["y_mm"], False)
    x1_px = mm_to_px(bf["x_mm"] + bf["w_mm"], True)
    y1_px = mm_to_px(bf["y_mm"] + bf["h_mm"], False)
    draw.rectangle([x0_px, y0_px, x1_px, y1_px], outline="black", width=12)

    # 2. 4 Corner Fiducial Markers
    for m in config["fiducial_markers"].values():
        mx0 = mm_to_px(m["x"], True)
        my0 = mm_to_px(m["y"], False)
        mx1 = mm_to_px(m["x"] + m["w"], True)
        my1 = mm_to_px(m["y"] + m["h"], False)
        draw.rectangle([mx0, my0, mx1, my1], fill="black")

    # 3. Middle Cut Line
    cut_y_px = mm_to_px(config["cut_line_y_mm"], False)
    dash_len = mm_to_px(2.5, True)
    gap_len = mm_to_px(1.5, True)
    cur_x = x0_px
    end_x = x1_px
    while cur_x < end_x:
        draw.line([cur_x, cut_y_px, min(cur_x + dash_len, end_x), cut_y_px], fill="#333333", width=4)
        cur_x += dash_len + gap_len

    # Center Cut Label
    cut_text = " -- [ CUT HERE : SEPARATE INTO 2 A5 ANSWER SHEETS ] -- "
    draw.rectangle([CANVAS_WIDTH_PX // 2 - 320, cut_y_px - 18, CANVAS_WIDTH_PX // 2 + 320, cut_y_px + 18], fill="white")
    draw.text((CANVAS_WIDTH_PX // 2, cut_y_px), cut_text, fill="black", font=font_bold, anchor="mm")

    # 4. Render Sheets
    for s_data in config["sheets"]:
        s_id = s_data["sheet_id"]
        y0_mm = s_data["y0_mm"]

        # Titles
        draw.text((CANVAS_WIDTH_PX // 2, mm_to_px(y0_mm + 4.5, False)), "KING MONGKUT'S UNIVERSITY OF TECHNOLOGY THONBURI", fill="black", font=font_title, anchor="mm")
        draw.text((CANVAS_WIDTH_PX // 2, mm_to_px(y0_mm + 8.5, False)), "ICE415 Digital Image Processing - OMR Answer Sheet", fill="black", font=font_sub, anchor="mm")
        draw.text((CANVAS_WIDTH_PX // 2, mm_to_px(y0_mm + 12.0, False)), f"Form: 40 Questions | 5 Options (A-E) | Pencil 2B Only | Sheet {s_id} [A5]", fill="#333333", font=font_small, anchor="mm")

        # Metadata Boxes
        # Left Box (Student ID)
        bx0 = mm_to_px(21.0, True)
        by0 = mm_to_px(y0_mm + 14.5, False)
        bx1 = mm_to_px(99.0, True)
        by1 = mm_to_px(y0_mm + 28.5, False)
        draw.rectangle([bx0, by0, bx1, by1], outline="black", width=3)
        draw.text((bx0 + 12, by0 + 8), "STUDENT ID (11 DIGITS):", fill="black", font=font_bold)
        for i in range(11):
            dbx0 = mm_to_px(22.5 + (i * 6.7), True)
            dby0 = mm_to_px(y0_mm + 19.5, False)
            dbx1 = dbx0 + mm_to_px(6.0, True)
            dby1 = dby0 + mm_to_px(7.0, False)
            draw.rectangle([dbx0, dby0, dbx1, dby1], outline="black", width=2)

        # Right Box (Name & Subject & Section)
        rx0 = mm_to_px(103.0, True)
        rx1 = mm_to_px(189.0, True)
        draw.rectangle([rx0, by0, rx1, by1], outline="black", width=3)
        draw.text((rx0 + 12, by0 + 8), "NAME - SURNAME:", fill="black", font=font_bold)
        draw.line([rx0 + 160, by0 + 26, rx1 - 15, by0 + 26], fill="black", width=2)
        draw.text((rx0 + 12, by0 + 44), "SUBJECT:", fill="black", font=font_bold)
        draw.line([rx0 + 105, by0 + 62, rx0 + 380, by0 + 62], fill="black", width=2)
        draw.text((rx0 + 395, by0 + 44), "SEC / RM:", fill="black", font=font_bold)
        draw.line([rx0 + 490, by0 + 62, rx1 - 15, by0 + 62], fill="black", width=2)

        # Instructions Bar
        ib_x0 = mm_to_px(21.0, True)
        ib_y0 = mm_to_px(y0_mm + 30.5, False)
        ib_x1 = mm_to_px(189.0, True)
        ib_y1 = mm_to_px(y0_mm + 35.3, False)
        draw.rectangle([ib_x0, ib_y0, ib_x1, ib_y1], fill="#eeeeee", outline="black", width=2)
        draw.text((CANVAS_WIDTH_PX // 2, (ib_y0 + ib_y1) // 2), "Instructions: Fill the oval completely with 2B pencil. Erase cleanly if changing. Do not fold or smudge.", fill="#222222", font=font_small, anchor="mm")

        # Column Dividers
        for div_mm in [56.5, 105.0, 153.5]:
            dx = mm_to_px(div_mm, True)
            dy_start = mm_to_px(y0_mm + 36.5, False)
            dy_end = mm_to_px(y0_mm + 122.5, False)
            draw.line([dx, dy_start, dx, dy_end], fill="#333333", width=3)

        # Column Headers (NO. A B C D E)
        col_hdrs = [
            {"qx": 13.0, "ax": 19.0},
            {"qx": 61.5, "ax": 67.5},
            {"qx": 110.0, "ax": 116.0},
            {"qx": 158.5, "ax": 164.5}
        ]
        hdr_y_px = mm_to_px(y0_mm + 38.5, False)
        for ch in col_hdrs:
            draw.text((mm_to_px(ch["qx"], True), hdr_y_px), "NO.", fill="black", font=font_q, anchor="mm")
            for oi, ol in enumerate(["A", "B", "C", "D", "E"]):
                ox_px = mm_to_px(ch["ax"] + (oi * config["bubble_pitch_x_mm"]), True)
                draw.text((ox_px, hdr_y_px), ol, fill="black", font=font_q, anchor="mm")

        # Questions & Bubbles
        for q in s_data["questions"]:
            qx_px = mm_to_px(q["q_x_mm"], True)
            qy_px = mm_to_px(q["q_y_mm"], False)
            draw.text((qx_px, qy_px), f"{q['q']:02d}", fill="black", font=font_q, anchor="mm")

            for opt_key, opt_data in q["options"].items():
                cx_px = mm_to_px(opt_data["cx_mm"], True)
                cy_px = mm_to_px(opt_data["cy_mm"], False)
                r_px = mm_to_px(opt_data["r_mm"], True)

                draw.ellipse([cx_px - r_px, cy_px - r_px, cx_px + r_px, cy_px + r_px], outline="black", width=3)
                draw.text((cx_px, cy_px), opt_key, fill="#777777", font=font_opt, anchor="mm")

        # Footer
        draw.text((CANVAS_WIDTH_PX // 2, mm_to_px(y0_mm + 126.5, False)), f"KMUTT Computer Engineering | ICE415 Robust Pencil OMR Project | Form: A5-40Q-Sheet{s_id}", fill="#555555", font=font_small, anchor="mm")

    img.save(output_path, dpi=(300, 300))
    print(f"✅ Generated 300 DPI PNG Canvas: {output_path}")

def main():
    print("==================================================")
    print("📄 ICE415 Robust Pencil OMR - Dual A5 Template")
    print("==================================================")

    config = build_template_coordinates()

    # 1. Save JSON config
    json_path = TEMPLATES_DIR / "template_config.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"✅ Generated Coordinates JSON: {json_path}")
    print(f"   Sheets: {config['sheets_count']} (Each A5)")
    print(f"   Questions per Sheet: {config['questions_per_sheet']}")
    print(f"   Total Bubble Points on Sheet 1: {len(config['questions']) * config['options_per_question']}")

    # 2. Save PDF
    pdf_path = TEMPLATES_DIR / "answer_sheet_a4.pdf"
    generate_pdf(config, pdf_path)

    # 3. Save 300 DPI Canvas PNG
    png_path = TEMPLATES_DIR / "answer_sheet_a4.png"
    generate_png_canvas(config, png_path)

    print("==================================================")
    print("🎉 Template Generation Complete!")
    print("==================================================")

if __name__ == "__main__":
    main()
