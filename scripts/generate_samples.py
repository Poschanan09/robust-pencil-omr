"""Generate realistic test samples for Robust Pencil OMR.
Course: ICE415 Digital Image Processing (KMUTT)

Generates:
1. app/static/img/samples/sample_2_filled_sheet.png (A5 cut sheet with 50 filled answers)
2. app/static/img/samples/sample_1_real_phone_photo.jpg (Realistic smartphone photo on wooden desk)
3. app/static/img/samples/sample_3_ambiguous_erasure.jpg (Sheet with eraser smudges & dual fills)
"""

import json
from pathlib import Path
import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = BASE_DIR / "templates" / "answer_sheet_a4.png"
CONFIG_PATH = BASE_DIR / "templates" / "template_config.json"
SAMPLES_DIR = BASE_DIR / "app" / "static" / "img" / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


def shade_bubble(image: np.ndarray, cx: int, cy: int, r: int, fill_intensity: float = 0.85):
    """Draw a realistic pencil shaded mark inside a circular bubble."""
    # Create circular mask for shading
    h, w = image.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    # Inner fill radius slightly smaller than boundary
    fill_r = max(2, int(r * 0.90))
    cv2.circle(mask, (cx, cy), fill_r, 255, -1)

    # Generate graphite texture (dark gray with realistic noise)
    base_val = int(255 * (1.0 - fill_intensity))
    noise = np.random.normal(loc=0, scale=12, size=(h, w)).astype(np.int16)
    pencil = np.clip(base_val + noise, 15, 230).astype(np.uint8)
    pencil_bgr = cv2.merge([pencil, pencil, pencil])

    # Slight blur to simulate soft graphite smearing
    pencil_bgr = cv2.GaussianBlur(pencil_bgr, (3, 3), 0.8)

    # Blend onto image
    in_mask = mask > 0
    image[in_mask] = pencil_bgr[in_mask]


def main():
    print("Loading base template and configuration...")
    full_sheet = cv2.imread(str(TEMPLATE_PATH))
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Sheet 1 is top half
    h_full, w_full = full_sheet.shape[:2]
    sheet1 = full_sheet[: h_full // 2, :].copy()

    # Deterministic answer key for 50 questions
    # Pattern: A, B, C, D, E repeating
    choices = ["A", "B", "C", "D", "E"]
    answers = [choices[i % 5] for i in range(50)]

    # 1. Generate Clean Filled A5 Sheet
    filled_sheet1 = sheet1.copy()
    for q_meta, ans in zip(cfg["questions"], answers):
        opt_info = q_meta["options"][ans]
        cx = opt_info["cx_px"]
        cy = opt_info["cy_px"]  # In full A4 coords, Sheet 1 is 0..1754 so cy_px matches directly
        r = opt_info["r_px"]
        shade_bubble(filled_sheet1, cx, cy, r, fill_intensity=0.88)

    clean_sample_path = SAMPLES_DIR / "sample_2_filled_sheet.png"
    cv2.imwrite(str(clean_sample_path), filled_sheet1)
    print(f"Saved: {clean_sample_path}")

    # 2. Generate Realistic Smartphone Photo on Wooden Desk
    # Desk background with warm wooden tone and subtle grain
    desk_w, desk_h = 3000, 2200
    desk = np.zeros((desk_h, desk_w, 3), dtype=np.uint8)
    # Warm table color (BGR: 110, 140, 175)
    desk[:, :, 0] = 105
    desk[:, :, 1] = 135
    desk[:, :, 2] = 170

    # Add realistic wood texture noise
    wood_noise = np.random.normal(0, 8, (desk_h, desk_w)).astype(np.int16)
    for c in range(3):
        desk[:, :, c] = np.clip(desk[:, :, c] + wood_noise, 0, 255).astype(np.uint8)

    # Project the filled sheet onto the desk with realistic camera angle & perspective
    sh_h, sh_w = filled_sheet1.shape[:2]
    src_corners = np.array([[0, 0], [sh_w, 0], [sh_w, sh_h], [0, sh_h]], dtype=np.float32)

    # Perspective target corners (slight tilt and perspective trapezoid)
    dst_corners = np.array([
        [420, 260],    # Top-Left
        [2620, 340],   # Top-Right
        [2510, 1920],  # Bottom-Right
        [340, 1840]    # Bottom-Left
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(src_corners, dst_corners)
    warped_sheet = cv2.warpPerspective(filled_sheet1, M, (desk_w, desk_h), flags=cv2.INTER_LINEAR)
    mask = cv2.warpPerspective(np.full((sh_h, sh_w), 255, dtype=np.uint8), M, (desk_w, desk_h), flags=cv2.INTER_NEAREST)

    # Soft drop shadow around the paper
    shadow_mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25)), iterations=2)
    shadow_blur = cv2.GaussianBlur(shadow_mask.astype(np.float32), (51, 51), 15) / 255.0
    shadow_factor = 1.0 - (shadow_blur * 0.35)
    for c in range(3):
        desk[:, :, c] = np.clip(desk[:, :, c].astype(np.float32) * shadow_factor, 0, 255).astype(np.uint8)

    # Natural lighting gradient (vignette from phone camera)
    y_coords, x_coords = np.ogrid[:desk_h, :desk_w]
    light_map = 1.0 - 0.15 * (((x_coords - 1500) / 1500)**2 + ((y_coords - 1100) / 1100)**2)
    light_map = np.clip(light_map, 0.70, 1.05)

    photo = desk.copy()
    photo[mask > 0] = warped_sheet[mask > 0]
    for c in range(3):
        photo[:, :, c] = np.clip(photo[:, :, c].astype(np.float32) * light_map, 0, 255).astype(np.uint8)

    # Slight mobile sensor noise
    sensor_noise = np.random.normal(0, 3, (desk_h, desk_w)).astype(np.int16)
    for c in range(3):
        photo[:, :, c] = np.clip(photo[:, :, c] + sensor_noise, 0, 255).astype(np.uint8)

    photo_sample_path = SAMPLES_DIR / "sample_1_real_phone_photo.jpg"
    cv2.imwrite(str(photo_sample_path), photo, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"Saved: {photo_sample_path}")

    # 3. Generate Ambiguous / Erasure Sample
    # Modify filled_sheet1: for Q7, Q19, Q34, add eraser smudge + second guess
    ambig_sheet = filled_sheet1.copy()
    # Q7: Ans is B, erase B to faint (0.28) and shade C (0.32) -> Ambiguous delta < 0.20
    q7_opts = cfg["questions"][6]["options"]
    shade_bubble(ambig_sheet, q7_opts["B"]["cx_px"], q7_opts["B"]["cy_px"], q7_opts["B"]["r_px"], fill_intensity=0.28)
    shade_bubble(ambig_sheet, q7_opts["C"]["cx_px"], q7_opts["C"]["cy_px"], q7_opts["C"]["r_px"], fill_intensity=0.33)

    # Q19: Ans is D, erase D to faint (0.22) and leave others blank -> Ambiguous (between Tlow and Thigh)
    q19_opts = cfg["questions"][18]["options"]
    shade_bubble(ambig_sheet, q19_opts["D"]["cx_px"], q19_opts["D"]["cy_px"], q19_opts["D"]["r_px"], fill_intensity=0.26)

    # Q34: Ans is D, shade both A (0.75) and D (0.80) -> Double fill
    q34_opts = cfg["questions"][33]["options"]
    shade_bubble(ambig_sheet, q34_opts["A"]["cx_px"], q34_opts["A"]["cy_px"], q34_opts["A"]["r_px"], fill_intensity=0.75)

    ambig_sample_path = SAMPLES_DIR / "sample_3_ambiguous_erasure.jpg"
    cv2.imwrite(str(ambig_sample_path), ambig_sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"Saved: {ambig_sample_path}")
    print("All sample images generated successfully!")


if __name__ == "__main__":
    main()
