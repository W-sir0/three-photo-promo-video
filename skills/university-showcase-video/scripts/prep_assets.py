#!/usr/bin/env python3
"""Prepare university showcase assets (emblem, campus landmark, portrait cutout, 3D icons) from config.json."""

import argparse
import colorsys
import json
import os
from collections import deque
import numpy as np
from PIL import Image, ImageFilter


def resolve_path(base_dir: str, p: str) -> str:
    if not p:
        return ""
    if os.path.isabs(p):
        return p
    return os.path.normpath(os.path.join(base_dir, p))


def hex_to_rgb(hex_str: str) -> np.ndarray:
    s = hex_str.strip().lstrip("#")
    return np.array([int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)], dtype=np.float32)


def smoothstep(edge0, edge1, x):
    diff = edge1 - edge0
    safe_diff = np.where(np.abs(diff) < 1e-5, 1e-5, diff)
    t = np.clip((x - edge0) / safe_diff, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ensure_parent(path: str):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def parse_crop_box(box, w: int, h: int):
    x0, y0, x1, y1 = [float(v) for v in box]
    if max(abs(x0), abs(y0), abs(x1), abs(y1)) <= 1.0:
        return (int(round(x0 * w)), int(round(y0 * h)), int(round(x1 * w)), int(round(y1 * h)))
    return (int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1)))


def prep_emblem(src_path: str, out_path: str):
    img = Image.open(src_path).convert("RGB")
    arr = np.array(img, dtype=np.float32)

    mask = arr.sum(axis=2) < 680
    ys, xs = np.where(mask)
    if len(ys) == 0:
        raise RuntimeError(f"Could not detect emblem bounds in {src_path}")

    cx = (xs.min() + xs.max()) / 2.0
    cy = (ys.min() + ys.max()) / 2.0
    rx = (xs.max() - xs.min()) / 2.0
    ry = (ys.max() - ys.min()) / 2.0
    r = max(rx, ry)

    size = 512
    cropped = img.crop((cx - r, cy - r, cx + r, cy + r)).resize((size, size), Image.Resampling.LANCZOS)

    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    dist_c = np.sqrt((xx - (size - 1) / 2.0) ** 2 + (yy - (size - 1) / 2.0) ** 2)
    mask_alpha = np.clip(254.8 - dist_c, 0.0, 1.0)

    c_arr = np.array(cropped, dtype=np.float32)
    outer_zone = (dist_c > 249.0) & (dist_c <= 255.5)
    bright_outer = outer_zone & (c_arr.sum(axis=2) > 650.0)
    mask_alpha = np.where(bright_outer, 0.0, mask_alpha)

    rgba = np.dstack([c_arr, mask_alpha * 255.0]).astype(np.uint8)
    ensure_parent(out_path)
    Image.fromarray(rgba, mode="RGBA").save(out_path)
    print(f"Saved {out_path} (512x512)")


def prep_campus(src_path: str, out_path: str, shadow_rgb: np.ndarray, hue_deg: float, opts: dict):
    img = Image.open(src_path).convert("RGB")
    w, h = img.size

    crop_box = opts.get("crop_box")
    if crop_box:
        box = parse_crop_box(crop_box, w, h)
        img = img.crop(box)
    else:
        trim_bottom = int(opts.get("trim_bottom_px", 0))
        if trim_bottom > 0 and trim_bottom < h - 40:
            img = img.crop((0, 0, w, h - trim_bottom))
        if opts.get("auto_symmetry_crop", True):
            arr_tmp = np.array(img, dtype=np.float32)
            ch, cw, _ = arr_tmp.shape
            y0, y1 = int(ch * 0.20), int(ch * 0.85)
            gray = arr_tmp[y0:y1, :, :].mean(axis=2)
            search_hw = min(int(cw * 0.30), 280)
            best_cx, best_diff = cw // 2, 1e18
            for cx in range(int(cw * 0.38), int(cw * 0.62)):
                hw_s = min(search_hw, cx, cw - cx)
                if hw_s < 40:
                    continue
                diff = float(np.mean(np.abs(gray[:, cx - hw_s:cx] - gray[:, cx:cx + hw_s][:, ::-1])))
                if diff < best_diff:
                    best_diff, best_cx = diff, cx
            hw_crop = min(best_cx, cw - best_cx)
            if hw_crop >= int(cw * 0.36):
                img = img.crop((best_cx - hw_crop, 0, best_cx + hw_crop, ch))

    cw, ch = img.size
    sky_mode = opts.get("sky_extend", "auto")
    need_sky = (sky_mode is True) or (sky_mode == "auto" and (cw / float(max(ch, 1))) > 2.0)

    if need_sky:
        crop_arr = np.array(img, dtype=np.float32)
        target_h = int(round(cw / 1.71))
        sky_ext_h = max(40, target_h - ch)
        top_strip = crop_arr[:min(6, ch), :, :].mean(axis=0)

        def blur_1d_row(row, radius):
            row_img = Image.fromarray(np.tile(row[None, :, :], (5, 1, 1)).astype(np.uint8))
            return np.array(row_img.filter(ImageFilter.GaussianBlur(radius=radius)), dtype=np.float32)[2]

        strip_soft = blur_1d_row(top_strip, 14.0)
        strip_wide = blur_1d_row(top_strip, 95.0)
        upper_sky_target = top_strip.mean(axis=0) * 0.90 + np.array([150.0, 178.0, 195.0], dtype=np.float32) * 0.10

        sky_rows = np.zeros((sky_ext_h, cw, 3), dtype=np.float32)
        for y in range(sky_ext_h):
            d = (sky_ext_h - 1 - y) / float(max(sky_ext_h - 1, 1))
            w_wide = np.clip(d * 2.4, 0.0, 1.0)
            w_wide = w_wide * w_wide * (3.0 - 2.0 * w_wide)
            base_row = strip_soft * (1.0 - w_wide) + strip_wide * w_wide
            w_top = d * d * (3.0 - 2.0 * d)
            sky_rows[y] = base_row * (1.0 - w_top) + upper_sky_target[None, :] * w_top

        seam_arr = crop_arr.copy()
        for y in range(min(10, ch)):
            wt = y / 10.0
            seam_arr[y] = strip_soft * (1.0 - wt) + crop_arr[y] * wt

        img = Image.fromarray(np.clip(np.vstack([sky_rows, seam_arr]), 0, 255).astype(np.uint8))
        cw, ch = img.size

    # Scale cleanly to width 1200 preserving aspect ratio
    target_w = 1200
    target_h = max(400, int(round(target_w * ch / float(cw))))
    upscaled = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    upscaled = upscaled.filter(ImageFilter.UnsharpMask(radius=1.1, percent=58, threshold=3))
    u = np.array(upscaled, dtype=np.float32)

    r, g, b = u[:, :, 0], u[:, :, 1], u[:, :, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    # 1. Tame harsh neon lawn greens/yellow-greens by ~38%
    green_dom = np.clip((g - np.maximum(r, b) * 0.90) / 35.0, 0.0, 1.0)
    yellow_green = np.clip(((r + g) * 0.5 - b - 18.0) / 40.0, 0.0, 1.0) * (g >= r * 0.92)
    foliage_mask = np.maximum(green_dom, yellow_green * 0.85)[:, :, None]
    desat_38 = lum[:, :, None] + 0.62 * (u - lum[:, :, None])
    u = u * (1.0 - foliage_mask) + desat_38 * foliage_mask

    # 2. Harmonize bright sky subtly toward theme mood
    if 205.0 <= hue_deg <= 250.0:
        sky_blue_mask = np.clip((b - r * 1.18) / 55.0, 0.0, 1.0) * np.clip((lum - 75.0) / 80.0, 0.0, 1.0)
        sky_blue_mask = sky_blue_mask[:, :, None] * 0.35
        sapphire_sky = np.array([58.0, 108.0, 186.0], dtype=np.float32)[None, None, :]
        u = u * (1.0 - sky_blue_mask) + sapphire_sky * sky_blue_mask
    else:
        sky_w = np.clip((lum - 140.0) / 80.0, 0.0, 1.0)[:, :, None] * 0.22
        mist_tint = shadow_rgb[None, None, :] * 0.45 + np.array([145.0, 152.0, 156.0], dtype=np.float32)[None, None, :] * 0.55
        u = u * (1.0 - sky_w) + mist_tint * sky_w

    # 3. Deepen overall exposure slightly (x0.85) & infuse shadow_tint
    u = u * 0.85
    lum2 = (0.299 * u[:, :, 0] + 0.587 * u[:, :, 1] + 0.114 * u[:, :, 2])[:, :, None]
    shadow_w = np.clip((112.0 - lum2) / 112.0, 0.0, 1.0) ** 1.32 * 0.32
    u = u * (1.0 - shadow_w) + shadow_rgb[None, None, :] * shadow_w

    ensure_parent(out_path)
    Image.fromarray(np.clip(u, 0, 255).astype(np.uint8), mode="RGB").save(out_path)
    print(f"Saved {out_path} ({target_w}x{target_h})")


def prep_portrait(src_path: str, mask_path: str, out_path: str, shadow_rgb: np.ndarray, opts: dict):
    img = Image.open(src_path).convert("RGB")
    if opts.get("restore_vintage", False):
        med = img.filter(ImageFilter.MedianFilter(size=3))
        restored = 0.65 * np.array(img, dtype=np.float32) + 0.35 * np.array(med, dtype=np.float32)
        img = Image.fromarray(np.clip(restored, 0, 255).astype(np.uint8))
    if opts.get("sharpen", True):
        img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=45, threshold=3))

    arr = np.array(img, dtype=np.float32)
    h, w, _ = arr.shape

    if mask_path and os.path.exists(mask_path):
        mask_img = Image.open(mask_path).convert("L").resize((w, h), Image.Resampling.LANCZOS)
        mask_f = np.array(mask_img, dtype=np.float32) / 255.0
        alpha = smoothstep(0.38, 0.78, mask_f)
        alpha = np.where(alpha < 0.04, 0.0, alpha)
    else:
        # Uniform studio background fallback: edge-connected BFS flood fill from top, left, and right ONLY
        bg_samples = np.concatenate([
            arr[:10, :10].reshape(-1, 3),
            arr[:10, -10:].reshape(-1, 3),
        ], axis=0)
        bg_color = np.median(bg_samples, axis=0)
        dist = np.linalg.norm(arr - bg_color[None, None, :], axis=2)

        ext = np.zeros((h, w), dtype=bool)
        visited = np.zeros((h, w), dtype=bool)
        q = deque()
        thresh_flood = 26.0

        seeds = [(0, x) for x in range(w)]
        for y in range(h - 1):
            seeds.append((y, 0))
            seeds.append((y, w - 1))

        neutral = (np.abs(arr[:, :, 0] - arr[:, :, 2]) < 14.0) & (dist <= 30.0)
        hy, hx = np.where(neutral[:int(0.28 * h), :])
        for sy, sx in zip(hy.tolist(), hx.tolist()):
            seeds.append((sy, sx))

        for sy, sx in seeds:
            if not visited[sy, sx] and dist[sy, sx] <= thresh_flood:
                visited[sy, sx] = True
                ext[sy, sx] = True
                q.append((sy, sx))

        while q:
            cy, cx = q.popleft()
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                    visited[ny, nx] = True
                    if dist[ny, nx] <= thresh_flood:
                        ext[ny, nx] = True
                        q.append((ny, nx))

        ext_u8 = Image.fromarray((ext.astype(np.uint8) * 255))
        dilated_1 = np.array(ext_u8.filter(ImageFilter.MaxFilter(3))) > 127
        dilated_2 = np.array(ext_u8.filter(ImageFilter.MaxFilter(5))) > 127
        boundary = dilated_2 & (~ext)

        alpha = np.where(ext, 0.0, 1.0).astype(np.float32)
        alpha = np.where(boundary, np.minimum(alpha, smoothstep(8.0, 38.0, dist)), alpha)
        near_gray = dilated_1 & (~ext) & (dist < 22.0)
        alpha = np.where(near_gray, smoothstep(8.0, 30.0, dist) * 0.7, alpha)

        alpha_img = Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8))
        alpha_soft = np.array(alpha_img.filter(ImageFilter.GaussianBlur(radius=0.65)), dtype=np.float32) / 255.0
        alpha = np.where(dilated_2, alpha_soft, 1.0)
        alpha[ext] = 0.0

    # 5x5 interior edge decontamination
    solid = alpha > 0.94
    decontam = arr.copy()
    solid_rgb = np.where(solid[:, :, None], arr, 0.0)
    solid_cnt = solid.astype(np.float32)
    sum_rgb = np.zeros_like(arr)
    sum_cnt = np.zeros((h, w), dtype=np.float32)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            y0, y1 = max(0, -dy), min(h, h - dy)
            x0, x1 = max(0, -dx), min(w, w - dx)
            sum_rgb[y0:y1, x0:x1] += solid_rgb[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
            sum_cnt[y0:y1, x0:x1] += solid_cnt[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
    has_solid = sum_cnt > 0.5
    avg_solid = sum_rgb / np.maximum(sum_cnt[:, :, None], 1.0)
    fringe = (alpha > 0.0) & (alpha < 0.94) & has_solid
    decontam = np.where(fringe[:, :, None], avg_solid, decontam)

    # Color harmonization (-13% saturation + subtle theme shadow tint)
    lum = (0.299 * decontam[:, :, 0] + 0.587 * decontam[:, :, 1] + 0.114 * decontam[:, :, 2])[:, :, None]
    graded = lum + 0.87 * (decontam - lum)
    shadow_weight = np.clip((85.0 - lum) / 85.0, 0.0, 1.0) * 0.18
    graded = graded * (1.0 - shadow_weight) + shadow_rgb[None, None, :] * shadow_weight

    rgba_full = np.dstack([np.clip(graded, 0, 255), np.clip(alpha * 255.0, 0, 255)]).astype(np.uint8)
    out_img = Image.fromarray(rgba_full, mode="RGBA")

    crop_box = opts.get("crop_box")
    if crop_box:
        out_img = out_img.crop(parse_crop_box(crop_box, w, h))

    if opts.get("flip_horizontal", False):
        out_img = out_img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    if opts.get("edge_taper", True):
        f_arr = np.array(out_img, dtype=np.float32)
        fh, fw, _ = f_arr.shape
        fa = f_arr[:, :, 3] / 255.0
        x_idx = np.arange(fw, dtype=np.float32)[None, :]
        if np.any(fa[:, 0] > 0.25):
            fa = fa * smoothstep(0.0, 0.065 * fw, x_idx)
        if np.any(fa[:, fw - 1] > 0.25):
            fa = fa * smoothstep(float(fw) - 1.0, float(fw) - 0.065 * fw, x_idx)
        f_arr[:, :, 3] = np.clip(fa * 255.0, 0, 255)
        out_img = Image.fromarray(f_arr.astype(np.uint8), mode="RGBA")

    ensure_parent(out_path)
    out_img.save(out_path)
    print(f"Saved {out_path} ({out_img.size})")


def prep_icon(raw_path: str, out_path: str):
    img = Image.open(raw_path).convert("RGB")
    arr = np.array(img, dtype=np.float32)
    h, w, _ = arr.shape

    border_pts = np.concatenate([
        arr[:12, :, :].reshape(-1, 3),
        arr[-12:, :, :].reshape(-1, 3),
        arr[:, :12, :].reshape(-1, 3),
        arr[:, -12:, :].reshape(-1, 3),
    ], axis=0)
    bg_level = np.percentile(border_pts.max(axis=1), 90)
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    max_ch = arr.max(axis=2)

    bg_thresh = max(24.0, bg_level + 12.0)
    ext = np.zeros((h, w), dtype=bool)
    visited = np.zeros((h, w), dtype=bool)
    q = deque()

    for x in range(w):
        for y in (0, h - 1):
            if not visited[y, x] and max_ch[y, x] <= bg_thresh:
                visited[y, x] = True
                ext[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if not visited[y, x] and max_ch[y, x] <= bg_thresh:
                visited[y, x] = True
                ext[y, x] = True
                q.append((y, x))

    while q:
        cy, cx = q.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                visited[ny, nx] = True
                if max_ch[ny, nx] <= bg_thresh:
                    ext[ny, nx] = True
                    q.append((ny, nx))

    enclosed_black = (~ext) & (max_ch <= bg_level + 6.0)
    bg_mask = ext | enclosed_black

    bg_u8 = Image.fromarray((bg_mask.astype(np.uint8) * 255))
    near_ext = (np.array(bg_u8.filter(ImageFilter.MaxFilter(7))) > 127) & (~bg_mask)

    alpha = np.where(bg_mask, 0.0, 1.0).astype(np.float32)
    edge_alpha = smoothstep(max(8.0, bg_level + 2.0), max(52.0, bg_level + 36.0), lum)
    alpha = np.where(near_ext, np.minimum(alpha, edge_alpha), alpha)

    rgb = arr.copy()
    valid_edge = near_ext & (alpha > 0.04) & (alpha < 0.98)
    boost = np.where(valid_edge, 1.0 / np.maximum(alpha, 0.18), 1.0)
    rgb = np.where(valid_edge[:, :, None], np.clip(rgb * np.minimum(boost[:, :, None], 2.2), 0, 255), rgb)

    fg = alpha > 0.05
    ys, xs = np.where(fg)
    if len(ys) == 0:
        raise RuntimeError(f"Empty icon foreground in {raw_path}")
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1

    rgba = np.dstack([np.clip(rgb, 0, 255), np.clip(alpha * 255.0, 0, 255)]).astype(np.uint8)
    cropped = Image.fromarray(rgba[y0:y1, x0:x1], mode="RGBA")

    canvas_size = 320
    target_span = 264
    cw, ch = cropped.size
    scale = target_span / float(max(cw, ch))
    nw, nh = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))
    resized = cropped.resize((nw, nh), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    canvas.paste(resized, ((canvas_size - nw) // 2, (canvas_size - nh) // 2), resized)

    ensure_parent(out_path)
    canvas.save(out_path)
    print(f"Saved {out_path} (320x320, subject={nw}x{nh})")


def build_qa_sheet(cfg: dict, base_dir: str):
    previews_dir = resolve_path(base_dir, cfg.get("previews_dir", "previews"))
    os.makedirs(previews_dir, exist_ok=True)
    bg_mid = tuple(int(v) for v in hex_to_rgb(cfg["palette"]["bg_mid"]))
    sheet = Image.new("RGB", (1320, 720), bg_mid)

    assets = cfg["assets"]
    p_path = resolve_path(base_dir, assets["portrait"])
    e_path = resolve_path(base_dir, assets["emblem"])
    c_path = resolve_path(base_dir, assets["campus"])

    if os.path.exists(p_path):
        p = Image.open(p_path).convert("RGBA")
        pw, ph = p.size
        p_r = p.resize((int(round(430 * pw / float(ph))), 430), Image.Resampling.LANCZOS)
        sheet.paste(p_r, (30, 145), p_r)

    if os.path.exists(e_path):
        e = Image.open(e_path).convert("RGBA").resize((250, 250), Image.Resampling.LANCZOS)
        sheet.paste(e, (515, 30), e)

    if os.path.exists(c_path):
        c = Image.open(c_path).convert("RGB")
        cw, ch = c.size
        c_r = c.resize((460, int(round(460 * ch / float(cw)))), Image.Resampling.LANCZOS)
        sheet.paste(c_r, (475, 340))

    y_positions = [35, 260, 485]
    for idx, disc in enumerate(cfg.get("disciplines", [])[:3]):
        ic_path = resolve_path(base_dir, disc["icon"])
        if os.path.exists(ic_path):
            ic = Image.open(ic_path).convert("RGBA").resize((205, 205), Image.Resampling.LANCZOS)
            sheet.paste(ic, (1040, y_positions[idx]), ic)

    qa_path = os.path.join(previews_dir, "assets_check.png")
    sheet.save(qa_path)
    print(f"Saved QA sheet: {qa_path}")


def main():
    parser = argparse.ArgumentParser(description="Prepare cutout and graded PNG assets for university showcase video.")
    parser.add_argument("--config", required=True, help="Path to config.json")
    args = parser.parse_args()

    cfg_path = os.path.abspath(args.config)
    base_dir = os.path.dirname(cfg_path)
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    palette = cfg["palette"]
    shadow_rgb = hex_to_rgb(palette.get("shadow_tint", palette["bg_outer"]))
    hue_deg = float(palette.get("hue_deg", 210.0))

    raw = cfg["raw_inputs"]
    assets = cfg["assets"]

    if raw.get("emblem") and os.path.exists(resolve_path(base_dir, raw["emblem"])):
        prep_emblem(resolve_path(base_dir, raw["emblem"]), resolve_path(base_dir, assets["emblem"]))

    if raw.get("campus") and os.path.exists(resolve_path(base_dir, raw["campus"])):
        prep_campus(
            resolve_path(base_dir, raw["campus"]),
            resolve_path(base_dir, assets["campus"]),
            shadow_rgb,
            hue_deg,
            cfg.get("campus_options", {}),
        )

    if raw.get("portrait") and os.path.exists(resolve_path(base_dir, raw["portrait"])):
        mask_p = resolve_path(base_dir, raw.get("portrait_mask", ""))
        prep_portrait(
            resolve_path(base_dir, raw["portrait"]),
            mask_p,
            resolve_path(base_dir, assets["portrait"]),
            shadow_rgb,
            cfg.get("portrait_options", {}),
        )

    for disc in cfg.get("disciplines", []):
        raw_ic = resolve_path(base_dir, disc.get("raw_icon", ""))
        out_ic = resolve_path(base_dir, disc["icon"])
        if raw_ic and os.path.exists(raw_ic):
            prep_icon(raw_ic, out_ic)
        elif os.path.exists(out_ic):
            print(f"Using pre-cut transparent icon: {out_ic}")
        else:
            print(f"Warning: missing icon for {disc.get('name', '?')}: {out_ic}")

    build_qa_sheet(cfg, base_dir)


if __name__ == "__main__":
    main()
