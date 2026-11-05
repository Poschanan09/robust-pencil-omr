"""OMR Answer Sheet & Template Configuration Generator
Course: ICE415 Digital Image Processing (KMUTT)

Generates:
1. templates/answer_sheet_a4.pdf (Printable vector A4 sheet with 2x A5 sets of 40Q, 8 corner fiducial markers)
2. templates/answer_sheet_a4.png (300 DPI 2480x3508 canonical image with 8 fiducial markers)
3. templates/template_config.json (Normalized coordinates for OMR grading)
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
    """Compute exact millimeter, pixel, and normalized coordinates for 2x A5 sheets on A4 with 8 markers."""
    bubble_radius_mm = 2.0  # Diameter = 4.0 mm
    row_height_mm = 7.2     # Vertical pitch = 7.2 mm (3.2mm vertical gap between bubbles)
    bubble_pitch_x = 5.8    # Center-to-center pitch between A, B, C, D, E (1.8mm horizontal gap)

    # Geometry for each A5 Sheet Frame
    frame_x = 7.0
    frame_w = 196.0
    frame_h = 136.5
    m_size = 9.0  # Fiducial square marker size: 9mm x 9mm
    margin = 2.5

    # 5 Columns of 10 Questions = 50 Questions per Sheet
    # Col 1: Q01-Q10, Col 2: Q11-Q20, Col 3: Q21-Q30, Col 4: Q31-Q40, Col 5: Q41-Q50
    cols_config = [
        {"col": 1, "q_start": 1,  "q_end": 10, "q_x": 13.5, "a_x": 19.0},
        {"col": 2, "q_start": 11, "q_end": 20, "q_x": 51.5, "a_x": 57.0},
        {"col": 3, "q_start": 21, "q_end": 30, "q_x": 89.5, "a_x": 95.0},
        {"col": 4, "q_start": 31, "q_end": 40, "q_x": 127.5, "a_x": 133.0},
        {"col": 5, "q_start": 41, "q_end": 50, "q_x": 165.5, "a_x": 171.0},
    ]

    # Two A5 Sheets on one A4 (Sheet 1 top, Sheet 2 bottom)
    sheet_offsets = [
        {
            "sheet_id": 1,
            "name": "Sheet 1 (Top A5)",
            "y0": 6.0,
            "frame": {"x_mm": frame_x, "y_mm": 6.0, "w_mm": frame_w, "h_mm": frame_h},
            "markers": {
                "top_left": {"x": frame_x + margin, "y": 6.0 + margin, "w": m_size, "h": m_size},
                "top_right": {"x": frame_x + frame_w - margin - m_size, "y": 6.0 + margin, "w": m_size, "h": m_size},
                "bottom_left": {"x": frame_x + margin, "y": 6.0 + frame_h - margin - m_size, "w": m_size, "h": m_size},
                "bottom_right": {"x": frame_x + frame_w - margin - m_size, "y": 6.0 + frame_h - margin - m_size, "w": m_size, "h": m_size}
            }
        },
        {
            "sheet_id": 2,
            "name": "Sheet 2 (Bottom A5)",
            "y0": 154.5,
            "frame": {"x_mm": frame_x, "y_mm": 154.5, "w_mm": frame_w, "h_mm": frame_h},
            "markers": {
                "top_left": {"x": frame_x + margin, "y": 154.5 + margin, "w": m_size, "h": m_size},
                "top_right": {"x": frame_x + frame_w - margin - m_size, "y": 154.5 + margin, "w": m_size, "h": m_size},
                "bottom_left": {"x": frame_x + margin, "y": 154.5 + frame_h - margin - m_size, "w": m_size, "h": m_size},
                "bottom_right": {"x": frame_x + frame_w - margin - m_size, "y": 154.5 + frame_h - margin - m_size, "w": m_size, "h": m_size}
            }
        }
    ]

    sheets = []
    all_markers_dict = {}

    for s_info in sheet_offsets:
        s_id = s_info["sheet_id"]
        y0 = s_info["y0"]
        start_y = y0 + 50.0

        for m_key, m_val in s_info["markers"].items():
            all_markers_dict[f"s{s_id}_{m_key}"] = m_val

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

                    # Normalized coordinates relative to the detected outer frame of this sheet
                    cx_pct = round((cx - frame_x) / frame_w, 5)
                    cy_pct = round((cy - y0) / frame_h, 5)
                    r_pct = round(bubble_radius_mm / frame_w, 5)

                    options[opt_label] = {
                        "cx_mm": round(cx, 2),
                        "cy_mm": round(cy, 2),
                        "r_mm": round(bubble_radius_mm, 2),
                        "cx_pct": cx_pct,
                        "cy_pct": cy_pct,
                        "r_pct": r_pct,
                        "cx_px": int(round((cx / PAGE_WIDTH_MM) * CANVAS_WIDTH_PX)),
                        "cy_px": int(round((cy / PAGE_HEIGHT_MM) * CANVAS_HEIGHT_PX)),
                        "r_px": int(round((bubble_radius_mm / PAGE_WIDTH_MM) * CANVAS_WIDTH_PX))
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
            "bounding_frame": s_info["frame"],
            "fiducial_markers": s_info["markers"],
            "questions": sheet_questions
        })

    config = {
        "template_name": "ICE415_Dual_A5_50Q_8Markers",
        "version": "2.2.0",
        "paper_size": "A4",
        "canvas_size": {
            "width_mm": PAGE_WIDTH_MM,
            "height_mm": PAGE_HEIGHT_MM,
            "width_px_300dpi": CANVAS_WIDTH_PX,
            "height_px_300dpi": CANVAS_HEIGHT_PX
        },
        "cut_line_y_mm": MID_Y_MM,
        "sheets_count": 2,
        "total_fiducial_markers": 8,
        "questions_per_sheet": 50,
        "questions_count": 50,
        "options_per_question": 5,
        "options_labels": ["A", "B", "C", "D", "E"],
        "bubble_diameter_mm": 4.0,
        "bubble_radius_mm": bubble_radius_mm,
        "bubble_pitch_x_mm": bubble_pitch_x,
        "row_height_y_mm": row_height_mm,
        "inner_mask_radius_ratio": 0.82,
        "sheets": sheets,
        # Default bounding frame & markers reference Sheet 1 for single-sheet grading
        "bounding_frame": sheets[0]["bounding_frame"],
        "fiducial_markers": sheets[0]["fiducial_markers"],
        "all_8_markers": all_markers_dict,
        "questions": sheets[0]["questions"],
        "sheet2_questions": sheets[1]["questions"]
    }

    return config

def generate_pdf(config: dict, output_path: Path):
    """Generate high-precision vector A4 PDF containing 2x A5 sheets with 8 corner fiducial markers."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.set_draw_color(0, 0, 0)

    # 1. Middle Horizontal Cut Line (dashed at 148.5 mm)
    cut_y = config["cut_line_y_mm"]
    pdf.set_line_width(0.35)
    pdf.set_dash_pattern(dash=2.5, gap=1.5)
    pdf.line(6.0, cut_y, 204.0, cut_y)
    pdf.set_dash_pattern()

    # Cut guide label badge in the center
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_fill_color(255, 255, 255)
    cut_label = "  -- [ CUT HERE : SEPARATE INTO 2 A5 SHEETS FOR 2 STUDENTS ] --  "
    lbl_w = pdf.get_string_width(cut_label) + 4
    pdf.set_xy((PAGE_WIDTH_MM - lbl_w) / 2, cut_y - 2.0)
    pdf.cell(lbl_w, 4, cut_label, align="C", fill=True)

    cols_headers = [
        {"qx": 13.5, "ax": 19.0},
        {"qx": 51.5, "ax": 57.0},
        {"qx": 89.5, "ax": 95.0},
        {"qx": 127.5, "ax": 133.0},
        {"qx": 165.5, "ax": 171.0}
    ]
    r = config["bubble_radius_mm"]

    # 2. Render both A5 sheets (Each has its own bounding box + 4 corner markers = 8 markers total)
    for s_data in config["sheets"]:
        s_id = s_data["sheet_id"]
        y0 = s_data["y0_mm"]
        bf = s_data["bounding_frame"]

        # Outer Frame for this A5 Sheet (1.0 mm stroke)
        pdf.set_line_width(1.0)
        pdf.rect(bf["x_mm"], bf["y_mm"], bf["w_mm"], bf["h_mm"])

        # 4 Corner Fiducial Markers for this sheet (solid black squares)
        pdf.set_fill_color(0, 0, 0)
        for m in s_data["fiducial_markers"].values():
            pdf.rect(m["x"], m["y"], m["w"], m["h"], style="F")

        # Header Titles
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_xy(25, y0 + 2.5)
        pdf.cell(160, 4.5, "KING MONGKUT'S UNIVERSITY OF TECHNOLOGY THONBURI", align="C")

        pdf.set_font("Helvetica", "B", 8.0)
        pdf.set_xy(25, y0 + 6.6)
        pdf.cell(160, 4.0, "ICE415 Digital Image Processing - OMR Answer Sheet", align="C")

        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_xy(25, y0 + 10.3)
        pdf.cell(160, 3.5, f"Form: 50 Questions | 5 Options (A-E) | Pencil 2B Only | Sheet {s_id} [A5]", align="C")

        # Student Metadata Boxes (Expanded height 19.5mm for comfortable handwriting)
        pdf.set_line_width(0.3)
        # Left Box: Student ID (11 Digits)
        box_top_y = y0 + 14.5
        box_h = 19.5
        pdf.rect(21.0, box_top_y, 78.0, box_h)
        pdf.set_font("Helvetica", "B", 7.0)
        pdf.set_xy(22.5, box_top_y + 1.6)
        pdf.cell(75.0, 3.5, "STUDENT ID (11 DIGITS):", align="L")

        digit_box_w = 6.0
        digit_box_h = 10.5
        digit_pitch = 6.7
        for d_i in range(11):
            dbx = 22.5 + (d_i * digit_pitch)
            dby = box_top_y + 6.0
            pdf.rect(dbx, dby, digit_box_w, digit_box_h)

        # Right Box: Student Name, Subject, Class/Section, Exam Date, Room
        pdf.rect(103.0, box_top_y, 86.0, box_h)
        pdf.set_font("Helvetica", "B", 7.0)

        # Line 1: Name (spacious room to write)
        pdf.set_xy(104.5, box_top_y + 1.8)
        pdf.cell(32.0, 3.5, "NAME - SURNAME:", align="L")
        pdf.set_line_width(0.25)
        pdf.line(136.0, box_top_y + 6.0, 187.0, box_top_y + 6.0)

        # Line 2: Subject & Class/Sec
        pdf.set_line_width(0.3)
        pdf.set_xy(104.5, box_top_y + 7.8)
        pdf.cell(16.0, 3.5, "SUBJECT:", align="L")
        pdf.set_line_width(0.2)
        pdf.line(120.0, box_top_y + 12.0, 153.0, box_top_y + 12.0)

        pdf.set_line_width(0.3)
        pdf.set_xy(155.0, box_top_y + 7.8)
        pdf.cell(16.0, 3.5, "CLASS / SEC:", align="L")
        pdf.set_line_width(0.2)
        pdf.line(174.0, box_top_y + 12.0, 187.0, box_top_y + 12.0)

        # Line 3: Exam Date & Seat / Room
        pdf.set_line_width(0.3)
        pdf.set_xy(104.5, box_top_y + 13.8)
        pdf.cell(16.0, 3.5, "EXAM DATE:", align="L")
        pdf.set_line_width(0.2)
        pdf.line(123.0, box_top_y + 18.0, 153.0, box_top_y + 18.0)

        pdf.set_line_width(0.3)
        pdf.set_xy(155.0, box_top_y + 13.8)
        pdf.cell(16.0, 3.5, "SEAT / ROOM:", align="L")
        pdf.set_line_width(0.2)
        pdf.line(175.0, box_top_y + 18.0, 187.0, box_top_y + 18.0)

        # Instructions Bar (shifted down)
        pdf.set_fill_color(240, 240, 240)
        pdf.set_line_width(0.25)
        pdf.rect(21.0, y0 + 36.0, 168.0, 4.8, style="FD")
        pdf.set_font("Helvetica", "I", 6.5)
        pdf.set_text_color(40, 40, 40)
        pdf.set_xy(21.0, y0 + 36.7)
        pdf.cell(168.0, 3.5, "Instructions: Fill the oval completely with 2B pencil. Erase cleanly if changing. Do not fold or smudge.", align="C")
        pdf.set_text_color(0, 0, 0)

        # Column Dividers (4 vertical lines between the 5 columns)
        pdf.set_line_width(0.35)
        dividers_x = [46.5, 84.5, 122.5, 160.5]
        for div_x in dividers_x:
            pdf.line(div_x, y0 + 42.0, div_x, y0 + 122.0)

        # Column Header Labels (NO. A B C D E)
        pdf.set_font("Helvetica", "B", 7.0)
        hdr_y = y0 + 43.0
        for col_hdr in cols_headers:
            pdf.set_xy(col_hdr["qx"] - 3.5, hdr_y)
            pdf.cell(7.0, 3.5, "NO.", align="C")
            for o_i, o_label in enumerate(["A", "B", "C", "D", "E"]):
                ox = col_hdr["ax"] + (o_i * config["bubble_pitch_x_mm"])
                pdf.set_xy(ox - r, hdr_y)
                pdf.cell(2 * r, 3.5, o_label, align="C")

        # Questions and Bubbles (50 Questions)
        pdf.set_line_width(0.3)
        for q in s_data["questions"]:
            pdf.set_font("Helvetica", "B", 7.0)
            pdf.set_xy(q["q_x_mm"] - 4.0, q["q_y_mm"] - 1.8)
            pdf.cell(7.0, 3.6, f"{q['q']:02d}", align="R")

            for opt_key, opt_data in q["options"].items():
                cx = opt_data["cx_mm"]
                cy = opt_data["cy_mm"]

                pdf.ellipse(cx - r, cy - r, 2 * r, 2 * r, style="D")

                pdf.set_font("Helvetica", "", 4.8)
                pdf.set_text_color(90, 90, 90)
                pdf.set_xy(cx - r, cy - 1.3)
                pdf.cell(2 * r, 2.6, opt_key, align="C")
                pdf.set_text_color(0, 0, 0)

        # Footer of each sheet
        pdf.set_font("Helvetica", "I", 6.0)
        pdf.set_xy(25.0, y0 + 126.5)
        pdf.cell(160.0, 3.5, f"KMUTT Computer Engineering | ICE415 Robust Pencil OMR Project | Form: A5-50Q-Sheet{s_id}", align="C")

    pdf.output(str(output_path))
    print(f"✅ Generated Vector PDF Answer Sheet: {output_path}")

def generate_png_canvas(config: dict, output_path: Path):
    """Generate high-resolution 300 DPI image (2480x3508) with all 8 fiducial markers using Pillow."""
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
        font_q = ImageFont.truetype("arialbd.ttf", 20)
        font_opt = ImageFont.truetype("arial.ttf", 14)
    except:
        font_title = ImageFont.load_default()
        font_sub = font_title
        font_small = font_title
        font_bold = font_title
        font_q = font_title
        font_opt = font_title

    # 1. Middle Cut Line
    cut_y_px = mm_to_px(config["cut_line_y_mm"], False)
    dash_len = mm_to_px(2.5, True)
    gap_len = mm_to_px(1.5, True)
    cur_x = mm_to_px(7.0, True)
    end_x = mm_to_px(203.0, True)
    while cur_x < end_x:
        draw.line([cur_x, cut_y_px, min(cur_x + dash_len, end_x), cut_y_px], fill="#444444", width=3)
        cur_x += dash_len + gap_len

    # Center Cut Label
    cut_text = " -- [ CUT HERE : SEPARATE INTO 2 A5 SHEETS FOR 2 STUDENTS ] -- "
    draw.rectangle([CANVAS_WIDTH_PX // 2 - 340, cut_y_px - 18, CANVAS_WIDTH_PX // 2 + 340, cut_y_px + 18], fill="white")
    draw.text((CANVAS_WIDTH_PX // 2, cut_y_px), cut_text, fill="black", font=font_bold, anchor="mm")

    # 2. Render each A5 sheet (Each with its own frame + 4 corner markers = 8 markers total)
    for s_data in config["sheets"]:
        s_id = s_data["sheet_id"]
        y0_mm = s_data["y0_mm"]
        bf = s_data["bounding_frame"]

        # Outer Frame for this A5 sheet
        x0_px = mm_to_px(bf["x_mm"], True)
        y0_px = mm_to_px(bf["y_mm"], False)
        x1_px = mm_to_px(bf["x_mm"] + bf["w_mm"], True)
        y1_px = mm_to_px(bf["y_mm"] + bf["h_mm"], False)
        draw.rectangle([x0_px, y0_px, x1_px, y1_px], outline="black", width=10)

        # 4 Corner Fiducial Markers for this sheet
        for m in s_data["fiducial_markers"].values():
            mx0 = mm_to_px(m["x"], True)
            my0 = mm_to_px(m["y"], False)
            mx1 = mm_to_px(m["x"] + m["w"], True)
            my1 = mm_to_px(m["y"] + m["h"], False)
            draw.rectangle([mx0, my0, mx1, my1], fill="black")

        # Titles
        draw.text((CANVAS_WIDTH_PX // 2, mm_to_px(y0_mm + 4.5, False)), "KING MONGKUT'S UNIVERSITY OF TECHNOLOGY THONBURI", fill="black", font=font_title, anchor="mm")
        draw.text((CANVAS_WIDTH_PX // 2, mm_to_px(y0_mm + 8.5, False)), "ICE415 Digital Image Processing - OMR Answer Sheet", fill="black", font=font_sub, anchor="mm")
        draw.text((CANVAS_WIDTH_PX // 2, mm_to_px(y0_mm + 12.0, False)), f"Form: 50 Questions | 5 Options (A-E) | Pencil 2B Only | Sheet {s_id} [A5]", fill="#333333", font=font_small, anchor="mm")

        # Metadata Boxes (Expanded height 19.5mm for comfortable handwriting)
        # Left Box (Student ID)
        bx0 = mm_to_px(21.0, True)
        by0 = mm_to_px(y0_mm + 14.5, False)
        bx1 = mm_to_px(99.0, True)
        by1 = mm_to_px(y0_mm + 34.0, False)
        draw.rectangle([bx0, by0, bx1, by1], outline="black", width=3)
        draw.text((bx0 + 12, by0 + 8), "STUDENT ID (11 DIGITS):", fill="black", font=font_bold)
        for i in range(11):
            dbx0 = mm_to_px(22.5 + (i * 6.7), True)
            dby0 = mm_to_px(y0_mm + 20.5, False)
            dbx1 = dbx0 + mm_to_px(6.0, True)
            dby1 = dby0 + mm_to_px(10.5, False)
            draw.rectangle([dbx0, dby0, dbx1, dby1], outline="black", width=2)

        # Right Box (Name & Subject & Section & Date - Spacious 3 Rows)
        rx0 = mm_to_px(103.0, True)
        rx1 = mm_to_px(189.0, True)
        draw.rectangle([rx0, by0, rx1, by1], outline="black", width=3)

        # Row 1: Name (spacious room to write)
        draw.text((rx0 + 12, by0 + 12), "NAME - SURNAME:", fill="black", font=font_bold)
        draw.line([rx0 + 175, by0 + 52, rx1 - 15, by0 + 52], fill="black", width=2)

        # Row 2: Subject & Class/Sec
        draw.text((rx0 + 12, by0 + 82), "SUBJECT:", fill="black", font=font_bold)
        draw.line([rx0 + 110, by0 + 122, rx0 + 390, by0 + 122], fill="black", width=2)
        draw.text((rx0 + 405, by0 + 82), "CLASS / SEC:", fill="black", font=font_bold)
        draw.line([rx0 + 535, by0 + 122, rx1 - 15, by0 + 122], fill="black", width=2)

        # Row 3: Exam Date & Seat/Room
        draw.text((rx0 + 12, by0 + 152), "EXAM DATE:", fill="black", font=font_bold)
        draw.line([rx0 + 135, by0 + 192, rx0 + 390, by0 + 192], fill="black", width=2)
        draw.text((rx0 + 405, by0 + 152), "SEAT / ROOM:", fill="black", font=font_bold)
        draw.line([rx0 + 545, by0 + 192, rx1 - 15, by0 + 192], fill="black", width=2)

        # Instructions Bar (shifted down)
        ib_x0 = mm_to_px(21.0, True)
        ib_y0 = mm_to_px(y0_mm + 36.0, False)
        ib_x1 = mm_to_px(189.0, True)
        ib_y1 = mm_to_px(y0_mm + 40.8, False)
        draw.rectangle([ib_x0, ib_y0, ib_x1, ib_y1], fill="#eeeeee", outline="black", width=2)
        draw.text((CANVAS_WIDTH_PX // 2, (ib_y0 + ib_y1) // 2), "Instructions: Fill the oval completely with 2B pencil. Erase cleanly if changing. Do not fold or smudge.", fill="#222222", font=font_small, anchor="mm")

        # Column Dividers (4 vertical lines between the 5 columns)
        for div_mm in [46.5, 84.5, 122.5, 160.5]:
            dx = mm_to_px(div_mm, True)
            dy_start = mm_to_px(y0_mm + 42.0, False)
            dy_end = mm_to_px(y0_mm + 122.0, False)
            draw.line([dx, dy_start, dx, dy_end], fill="#333333", width=3)

        # Column Headers (NO. A B C D E for 5 columns)
        col_hdrs = [
            {"qx": 13.5, "ax": 19.0},
            {"qx": 51.5, "ax": 57.0},
            {"qx": 89.5, "ax": 95.0},
            {"qx": 127.5, "ax": 133.0},
            {"qx": 165.5, "ax": 171.0}
        ]
        hdr_y_px = mm_to_px(y0_mm + 44.5, False)
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
        draw.text((CANVAS_WIDTH_PX // 2, mm_to_px(y0_mm + 128.5, False)), f"KMUTT Computer Engineering | ICE415 Robust Pencil OMR Project | Form: A5-50Q-Sheet{s_id}", fill="#555555", font=font_small, anchor="mm")

    img.save(output_path, dpi=(300, 300))
    print(f"✅ Generated 300 DPI PNG Canvas: {output_path}")

def main():
    print("==================================================")
    print("📄 ICE415 Robust Pencil OMR - Dual A5 Template (8 Markers)")
    print("==================================================")

    config = build_template_coordinates()

    # 1. Save JSON config
    json_path = TEMPLATES_DIR / "template_config.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"✅ Generated Coordinates JSON: {json_path}")
    print(f"   Sheets: {config['sheets_count']} (Each A5)")
    print(f"   Total Fiducial Markers: {config['total_fiducial_markers']} (4 per sheet)")
    print(f"   Questions per Sheet: {config['questions_per_sheet']}")

    # 2. Save PDF
    pdf_path = TEMPLATES_DIR / "answer_sheet_a4.pdf"
    generate_pdf(config, pdf_path)

    # 3. Save 300 DPI Canvas PNG
    png_path = TEMPLATES_DIR / "answer_sheet_a4.png"
    generate_png_canvas(config, png_path)

    print("==================================================")
    print("🎉 Template Generation Complete with 8 Markers!")
    print("==================================================")

if __name__ == "__main__":
    main()
