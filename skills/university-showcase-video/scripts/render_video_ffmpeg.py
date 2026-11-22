#!/usr/bin/env python3
"""Cross-platform Python (Pillow + NumPy + FFmpeg) renderer for university-showcase-video."""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def resolve_path(base_dir: str, p: str) -> str:
    if not p:
        return ""
    if os.path.isabs(p):
        return p
    return os.path.normpath(os.path.join(base_dir, p))


def hex_to_rgb(hex_str: str):
    s = hex_str.strip().lstrip("#")
    if len(s) != 6:
        return (20, 50, 100)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def clamp(x: float, a: float, b: float) -> float:
    return min(max(x, a), b)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def progress(t: float, start: float, end: float) -> float:
    if end <= start:
        return 1.0 if t >= end else 0.0
    return clamp((t - start) / (end - start), 0.0, 1.0)


def ease_in_out_cubic(t: float) -> float:
    x = clamp(t, 0.0, 1.0)
    return 4.0 * x * x * x if x < 0.5 else 1.0 - ((-2.0 * x + 2.0) ** 3) / 2.0


def ease_out_quart(t: float) -> float:
    x = clamp(t, 0.0, 1.0)
    return 1.0 - (1.0 - x) ** 4


def ease_out_cubic(t: float) -> float:
    x = clamp(t, 0.0, 1.0)
    return 1.0 - (1.0 - x) ** 3


def ease_out_back(t: float, overshoot: float = 1.15) -> float:
    x = clamp(t, 0.0, 1.0)
    c1 = overshoot
    c3 = c1 + 1.0
    return 1.0 + c3 * ((x - 1.0) ** 3) + c1 * ((x - 1.0) ** 2)


def find_font(candidates, size: int) -> ImageFont.FreeTypeFont:
    for path, idx in candidates:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=idx)
            except Exception:
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
    return ImageFont.load_default()


def load_fonts(cfg: dict, u: float) -> dict:
    overrides = cfg.get("fonts", {})

    def pick(key, candidates, size):
        ov = overrides.get(key)
        if isinstance(ov, dict):
            candidates = [(ov.get("path", ""), int(ov.get("index", 0)))] + candidates
        elif isinstance(ov, str) and ov:
            candidates = [(ov, 0)] + candidates
        return find_font(candidates, max(10, int(round(size))))

    cjk_serif_bold = [
        ("/System/Library/Fonts/Supplemental/Songti.ttc", 1),
        ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", 2),
        ("/usr/share/fonts/noto-cjk/NotoSerifCJK-Bold.ttc", 2),
        ("/usr/share/fonts/truetype/noto/NotoSerifCJK-Bold.ttc", 0),
        ("C:/Windows/Fonts/simsun.ttc", 0),
    ]
    cjk_sans_med = [
        ("/System/Library/Fonts/STHeiti Medium.ttc", 1),
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", 2),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc", 2),
        ("/usr/share/fonts/noto-cjk/NotoSansCJK-Medium.ttc", 2),
        ("C:/Windows/Fonts/msyhbd.ttc", 0),
    ]
    cjk_sans_reg = [
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
        ("/System/Library/Fonts/STHeiti Light.ttc", 1),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 2),
        ("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc", 2),
        ("C:/Windows/Fonts/msyh.ttc", 0),
    ]
    en_serif = [
        ("/System/Library/Fonts/Supplemental/Georgia.ttf", 0),
        ("/System/Library/Fonts/Supplemental/Times New Roman.ttf", 0),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 0),
        ("C:/Windows/Fonts/georgia.ttf", 0),
    ]

    return {
        "title_cn": pick("title_cn", cjk_serif_bold, 46 * u),
        "title_en": pick("title_en", en_serif, 17 * u),
        "name": pick("person_name", cjk_serif_bold, 36 * u),
        "role": pick("person_title", cjk_sans_reg, 16.5 * u),
        "label": pick("discipline_label", cjk_sans_med, 17 * u),
        "motto_tag": pick("motto_label", cjk_sans_med, 16 * u),
        "motto_main": pick("motto_main", cjk_serif_bold, 37 * u),
    }


def draw_tracked_text(
    base_img: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill_rgba: tuple,
    x: float,
    top_y: float,
    tracking: float = 0.0,
    align: str = "left",
    shadow_rgba: tuple = None,
    shadow_blur: float = 0.0,
    shadow_offset_y: float = 2.0,
):
    if not text:
        return
    # Measure total width with per-character tracking
    char_widths = []
    max_h = 0
    dummy = ImageDraw.Draw(base_img)
    for ch in text:
        bbox = dummy.textbbox((0, 0), ch, font=font)
        adv = dummy.textlength(ch, font=font)
        char_widths.append(adv)
        max_h = max(max_h, bbox[3] - bbox[1])
    total_w = sum(char_widths) + tracking * max(0, len(text) - 1)
    start_x = x - total_w / 2.0 if align == "center" else x

    pad = int(max(12, shadow_blur * 2 + 8))
    lw = int(math.ceil(total_w)) + pad * 2
    lh = int(math.ceil(max_h * 1.6)) + pad * 2
    txt_layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(txt_layer)

    cur_x = float(pad)
    for ch, cw in zip(text, char_widths):
        tdraw.text((cur_x, float(pad)), ch, font=font, fill=fill_rgba)
        cur_x += cw + tracking

    ox = int(round(start_x)) - pad
    oy = int(round(top_y)) - pad

    if shadow_rgba is not None and shadow_rgba[3] > 0:
        sh = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(sh)
        cur_x = float(pad)
        for ch, cw in zip(text, char_widths):
            sdraw.text((cur_x, float(pad)), ch, font=font, fill=shadow_rgba)
            cur_x += cw + tracking
        if shadow_blur > 0.5:
            sh = sh.filter(ImageFilter.GaussianBlur(radius=shadow_blur * 0.55))
        base_img.alpha_composite(sh, (ox, oy + int(round(shadow_offset_y))))

    base_img.alpha_composite(txt_layer, (ox, oy))


def build_background_base(W: int, H: int, palette: dict) -> Image.Image:
    sx, sy = W / 1332.0, H / 720.0
    u = min(sx, sy)

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # Radial vignette centered behind apex (666*sx, 205..260*sy)
    cx, cy = 666.0 * sx, 225.0 * sy
    r_norm = np.clip(np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (880.0 * u), 0.0, 1.0)

    c0 = np.array(hex_to_rgb(palette["bg_center"]), dtype=np.float32)
    c1 = np.array(hex_to_rgb(palette["bg_mid"]), dtype=np.float32)
    c2 = np.array(hex_to_rgb(palette["bg_outer"]), dtype=np.float32)
    c3 = np.array(hex_to_rgb(palette["bg_bottom"]), dtype=np.float32)

    img_arr = np.zeros((H, W, 3), dtype=np.float32)
    locs = [0.0, 0.36, 0.74, 1.0]
    cols = [c0, c1, c2, c3]
    for i in range(3):
        t = np.clip((r_norm - locs[i]) / (locs[i + 1] - locs[i]), 0.0, 1.0)[:, :, None]
        mask = ((r_norm >= locs[i]) & (r_norm <= locs[i + 1] if i == 2 else r_norm < locs[i + 1]))[:, :, None]
        img_arr = np.where(mask, cols[i][None, None, :] * (1.0 - t) + cols[i + 1][None, None, :] * t, img_arr)

    # Bottom grounding shade
    bot_t = np.clip((yy - 480.0 * sy) / (240.0 * sy), 0.0, 1.0)[:, :, None] * 0.80
    img_arr = img_arr * (1.0 - bot_t) + c3[None, None, :] * bot_t

    # Deterministic organic grain
    rng = np.random.default_rng(42)
    grain = rng.integers(-5, 6, size=(H, W, 1), dtype=np.int16).astype(np.float32)
    img_arr = np.clip(img_arr + grain, 0, 255).astype(np.uint8)

    base = Image.fromarray(img_arr, mode="RGB").convert("RGBA")

    # Faint concentric architectural arcs behind apex
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    acx, acy = 666.0 * sx, 152.0 * sy
    for idx, r in enumerate([132, 198, 286, 392, 520]):
        rr = r * u
        a = 12 if idx % 2 == 0 else 7
        odraw.ellipse([acx - rr, acy - rr, acx + rr, acy + rr], outline=(238, 224, 188, a), width=max(1, int(round(u))))
    base.alpha_composite(overlay)
    return base


def make_particles(W: int, H: int):
    rng = np.random.default_rng(12345)
    pts = []
    scale = H / 720.0
    for i in range(24):
        pts.append({
            "x0": float((40.0 + rng.random() * 1252.0) * (W / 1332.0)),
            "y0": float((20.0 + rng.random() * 680.0) * scale),
            "r": float((1.4 + rng.random() * 2.8) * scale),
            "speedY": float((11.0 + rng.random() * 14.0) * scale),
            "driftX": float((6.0 + rng.random() * 10.0) * scale),
            "phase": float(rng.random() * math.pi * 2.0),
            "alpha": float(0.08 + rng.random() * 0.14),
            "warm": (i % 3 == 0),
        })
    return pts


def make_gold_gradient(W: int, H: int) -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # Diagonal projection from bottom-left to top-right
    t = np.clip((xx / float(W) * 0.65 + (1.0 - yy / float(H)) * 0.35), 0.0, 1.0)
    stops = [0.0, 0.35, 0.68, 1.0]
    cols = [
        np.array([246, 235, 201], dtype=np.float32),
        np.array([198, 174, 122], dtype=np.float32),
        np.array([242, 228, 188], dtype=np.float32),
        np.array([154, 130, 83], dtype=np.float32),
    ]
    out = np.zeros((H, W, 3), dtype=np.float32)
    for i in range(3):
        w = np.clip((t - stops[i]) / (stops[i + 1] - stops[i]), 0.0, 1.0)[:, :, None]
        m = ((t >= stops[i]) & (t <= stops[i + 1] if i == 2 else t < stops[i + 1]))[:, :, None]
        out = np.where(m, cols[i][None, None, :] * (1.0 - w) + cols[i + 1][None, None, :] * w, out)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGB").convert("RGBA")


def make_ribbon_image(W_rib: int, H_rib: int, rgb: tuple) -> Image.Image:
    x = np.linspace(0.0, 1.0, W_rib, dtype=np.float32)[None, :]
    a = np.where(x <= 0.58, lerp(0.84, 0.60, x / 0.58), lerp(0.60, 0.0, (x - 0.58) / 0.42))
    arr = np.zeros((H_rib, W_rib, 4), dtype=np.uint8)
    arr[:, :, 0] = rgb[0]
    arr[:, :, 1] = rgb[1]
    arr[:, :, 2] = rgb[2]
    arr[:, :, 3] = np.tile((np.clip(a, 0, 1) * 255).astype(np.uint8), (H_rib, 1))
    return Image.fromarray(arr, mode="RGBA")


def render_frame(res: dict, t: float) -> Image.Image:
    cfg = res["cfg"]
    W, H = res["W"], res["H"]
    DURATION = res["DURATION"]
    sx, sy = W / 1332.0, H / 720.0
    u = min(sx, sy)
    pal = cfg["palette"]
    scrim_rgb = hex_to_rgb(pal.get("scrim_color", pal["bg_bottom"]))
    sub_rgb = hex_to_rgb(pal.get("subtitle_color", "#D4E1F5"))
    emblem_rgb = hex_to_rgb(pal["emblem_accent"])

    frame = res["bg_base"].copy()

    # Bokeh specks
    bokeh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(bokeh)
    for pt in res["particles"]:
        y = (pt["y0"] - pt["speedY"] * t) % float(H)
        x = pt["x0"] + math.sin(t * 0.9 + pt["phase"]) * pt["driftX"]
        pulse = 0.72 + 0.28 * math.sin(t * 1.7 + pt["phase"])
        a = int(round(255 * pt["alpha"] * pulse))
        c = (246, 232, 196, a) if pt["warm"] else (*sub_rgb, a)
        r = pt["r"]
        bdraw.ellipse([x - r, y - r, x + r, y + r], fill=c)
    frame.alpha_composite(bokeh)

    # Timeline parameters
    emblem_alpha = ease_out_cubic(progress(t, 0.05, 0.34))
    emblem_intro_scale = lerp(0.76, 1.00, ease_out_back(progress(t, 0.05, 0.40), 1.15))
    ring_sweep = ease_out_cubic(progress(t, 0.08, 0.42))

    p_rise = ease_in_out_cubic(progress(t, 0.48, 0.96))
    apex_x = 666.0 * sx
    emblem_cy = lerp(360.0 * sy, 152.0 * sy, p_rise)
    outer_r = lerp(116.0 * u, 104.0 * u, p_rise) * emblem_intro_scale
    bezel_inner_r = outer_r * (97.5 / 104.0)
    emblem_r = outer_r * (94.5 / 104.0)

    tri_slope = (561.0 * sx) / (593.0 * sy)
    tri_alpha = 0.0 if t <= 0.48 else ease_out_cubic(progress(t, 0.48, 0.56))
    drop_t = ease_out_quart(progress(t, 0.48, 0.70))
    tri_apex_y = emblem_cy
    tri_bot_y = lerp(emblem_cy, 745.0 * sy, drop_t)

    motto_x = float(cfg.get("layout", {}).get("motto_x", 820.0))

    # Layer 2: Rising Golden Triangle + Campus + Scrim
    if tri_alpha > 0.005 and (tri_bot_y - tri_apex_y) > 6.0:
        tri_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        half_w = max(1.0, (tri_bot_y - tri_apex_y) * tri_slope)
        tri_pts = [(apex_x, tri_apex_y), (apex_x + half_w, tri_bot_y), (apex_x - half_w, tri_bot_y)]

        tri_mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(tri_mask).polygon(tri_pts, fill=255)

        kb_scale = 1.0 + 0.048 * progress(t, 0.48, DURATION)
        campus_src = res["campus"]
        cw_s, ch_s = campus_src.size
        campus_w = int(round(1140.0 * sx * kb_scale))
        campus_h = int(round(campus_w * ch_s / float(cw_s)))
        target_cy = float(cfg.get("layout", {}).get("campus_y", 448.0)) * sy
        campus_cy = lerp(520.0 * sy, target_cy, p_rise)
        cx0 = int(round(apex_x - campus_w * 0.5))
        cy0 = int(round(campus_cy - campus_h * 0.5))

        campus_resized = campus_src.resize((campus_w, campus_h), Image.Resampling.BILINEAR)
        campus_canvas = Image.new("RGBA", (W, H), (*hex_to_rgb(pal["bg_bottom"]), 255))
        campus_canvas.paste(campus_resized, (cx0, cy0))

        # Bottom dark scrim + radial dark pool behind motto
        scrim_y0 = int(max(0, round(tri_bot_y - 315.0 * sy)))
        scrim_y1 = int(min(H, round(tri_bot_y)))
        if scrim_y1 > scrim_y0:
            yy_s = np.arange(scrim_y0, scrim_y1, dtype=np.float32)
            t_s = (yy_s - (tri_bot_y - 315.0 * sy)) / max(315.0 * sy, 1.0)
            a_s = np.where(t_s < 0.54, lerp(0.0, 0.58, t_s / 0.54), lerp(0.58, 0.90, (t_s - 0.54) / 0.46))
            scrim_arr = np.zeros((scrim_y1 - scrim_y0, W, 4), dtype=np.uint8)
            scrim_arr[:, :, 0] = scrim_rgb[0]
            scrim_arr[:, :, 1] = scrim_rgb[1]
            scrim_arr[:, :, 2] = scrim_rgb[2]
            scrim_arr[:, :, 3] = np.clip(a_s[:, None] * 255.0, 0, 255).astype(np.uint8)
            campus_canvas.alpha_composite(Image.fromarray(scrim_arr, mode="RGBA"), (0, scrim_y0))

        # Radial dark pool at (motto_x+95, 625)
        pool_cx = (motto_x + 95.0) * sx
        pool_cy = 625.0 * sy
        pool_r = 245.0 * u
        py0, py1 = max(0, int(pool_cy - pool_r)), min(H, int(pool_cy + pool_r))
        px0, px1 = max(0, int(pool_cx - pool_r)), min(W, int(pool_cx + pool_r))
        if py1 > py0 and px1 > px0:
            pyg, pxg = np.mgrid[py0:py1, px0:px1].astype(np.float32)
            pr = np.clip(1.0 - np.sqrt((pxg - pool_cx) ** 2 + (pyg - pool_cy) ** 2) / pool_r, 0.0, 1.0)
            pa = np.clip(pr * 0.62 * 255.0, 0, 255).astype(np.uint8)
            pool_arr = np.zeros((py1 - py0, px1 - px0, 4), dtype=np.uint8)
            pool_arr[:, :, 0], pool_arr[:, :, 1], pool_arr[:, :, 2], pool_arr[:, :, 3] = scrim_rgb[0], scrim_rgb[1], scrim_rgb[2], pa
            campus_canvas.alpha_composite(Image.fromarray(pool_arr, mode="RGBA"), (px0, py0))

        tri_layer.paste(campus_canvas, (0, 0), tri_mask)

        # Gold triangle border using gradient mask
        border_mask = Image.new("L", (W, H), 0)
        b_draw = ImageDraw.Draw(border_mask)
        bw = max(2, int(round(5.5 * u)))
        b_draw.line([tri_pts[0], tri_pts[1]], fill=255, width=bw)
        b_draw.line([tri_pts[0], tri_pts[2]], fill=255, width=bw)
        tri_layer.paste(res["gold_grad"], (0, 0), border_mask)

        if tri_alpha < 0.999:
            arr_t = np.array(tri_layer, dtype=np.float32)
            arr_t[:, :, 3] *= tri_alpha
            tri_layer = Image.fromarray(arr_t.astype(np.uint8), mode="RGBA")
        frame.alpha_composite(tri_layer)

    # Layer 3: Circular School Emblem
    if emblem_alpha > 0.005:
        ex, ey = apex_x, emblem_cy
        emb_sz = max(4, int(round(outer_r * 2 + 24)))
        emb_layer = Image.new("RGBA", (emb_sz, emb_sz), (0, 0, 0, 0))
        ec = emb_sz / 2.0

        # Shadow disc
        sh_layer = Image.new("RGBA", (emb_sz, emb_sz), (0, 0, 0, 0))
        ImageDraw.Draw(sh_layer).ellipse([ec - emblem_r, ec - emblem_r, ec + emblem_r, ec + emblem_r], fill=(*scrim_rgb, 155))
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(radius=6.0 * u))
        emb_layer.alpha_composite(sh_layer, (0, int(round(3 * u))))

        # Gold outer bezel sweep
        if ring_sweep > 0.005:
            bez_mask = Image.new("L", (emb_sz, emb_sz), 0)
            bd = ImageDraw.Draw(bez_mask)
            if ring_sweep >= 0.999:
                bd.ellipse([ec - outer_r, ec - outer_r, ec + outer_r, ec + outer_r], fill=255)
            else:
                bd.pieslice([ec - outer_r, ec - outer_r, ec + outer_r, ec + outer_r], start=-90, end=-90 + 360 * ring_sweep, fill=255)
            bd.ellipse([ec - bezel_inner_r, ec - bezel_inner_r, ec + bezel_inner_r, ec + bezel_inner_r], fill=0)
            gold_crop = res["gold_grad"].resize((emb_sz, emb_sz), Image.Resampling.BILINEAR)
            emb_layer.paste(gold_crop, (0, 0), bez_mask)

        # Emblem accent inner ring + white disc + emblem PNG
        ed = ImageDraw.Draw(emb_layer)
        ed.ellipse([ec - bezel_inner_r, ec - bezel_inner_r, ec + bezel_inner_r, ec + bezel_inner_r], fill=(*emblem_rgb, 255))
        ed.ellipse([ec - emblem_r, ec - emblem_r, ec + emblem_r, ec + emblem_r], fill=(255, 255, 255, 255))

        er_d = max(4, int(round(emblem_r * 2)))
        em_res = res["emblem"].resize((er_d, er_d), Image.Resampling.BILINEAR)
        em_x0 = int(round(ec - er_d * 0.5))
        emb_layer.alpha_composite(em_res, (em_x0, em_x0))

        if emblem_alpha < 0.999:
            ea = np.array(emb_layer, dtype=np.float32)
            ea[:, :, 3] *= emblem_alpha
            emb_layer = Image.fromarray(ea.astype(np.uint8), mode="RGBA")
        frame.alpha_composite(emb_layer, (int(round(ex - ec)), int(round(ey - ec))))

    # Layer 4: Top-Left Title
    p_title = ease_out_cubic(progress(t, 0.62, 0.94))
    if p_title > 0.005:
        tdx = lerp(-18.0 * sx, 0.0, p_title)
        a_t = int(round(255 * p_title))
        draw_tracked_text(
            frame, cfg["university"]["name"], res["fonts"]["title_cn"],
            (246, 249, 255, a_t), 56.0 * sx + tdx, 52.0 * sy, tracking=3.0 * u,
            shadow_rgba=(*scrim_rgb, int(round(130 * p_title))), shadow_blur=8 * u, shadow_offset_y=3 * u,
        )
        draw_tracked_text(
            frame, cfg["university"]["english_name"], res["fonts"]["title_en"],
            (*sub_rgb, a_t), 58.0 * sx + tdx, 108.0 * sy, tracking=0.8 * u,
            shadow_rgba=(*scrim_rgb, int(round(120 * p_title))), shadow_blur=5 * u, shadow_offset_y=2 * u,
        )

    # Layer 5: Portrait & Nameplate
    p_port_move = ease_out_quart(progress(t, 0.64, 1.00))
    portrait_alpha = ease_out_cubic(progress(t, 0.64, 0.92))
    if portrait_alpha > 0.005:
        pdx = lerp(-16.0 * sx, 0.0, p_port_move)
        pdy = lerp(24.0 * sy, 0.0, p_port_move)
        bar_rev = ease_out_cubic(progress(t, 0.72, 1.04))

        p_src = res["portrait"]
        pw_s, ph_s = p_src.size
        p_h = int(round(float(cfg.get("layout", {}).get("portrait_height", 450.0)) * sy))
        p_w = int(round(p_h * pw_s / float(ph_s)))
        p_cx = float(cfg.get("layout", {}).get("portrait_x", 236.0)) * sx
        px = int(round(p_cx - p_w * 0.5 + pdx))
        py = int(round(H - p_h + pdy))

        p_res = p_src.resize((p_w, p_h), Image.Resampling.BILINEAR)
        if portrait_alpha < 0.999:
            pa = np.array(p_res, dtype=np.float32)
            pa[:, :, 3] *= portrait_alpha
            p_res = Image.fromarray(pa.astype(np.uint8), mode="RGBA")
        frame.alpha_composite(p_res, (px, py))

        rib = res["ribbon_img"]
        if portrait_alpha < 0.999:
            ra = np.array(rib, dtype=np.float32)
            ra[:, :, 3] *= portrait_alpha
            rib = Image.fromarray(ra.astype(np.uint8), mode="RGBA")
        frame.alpha_composite(rib, (int(round(46.0 * sx + pdx)), int(round(576.0 * sy + pdy))))

        bar_h = int(round(84.0 * sy * bar_rev))
        if bar_h > 1:
            bar_w = max(2, int(round(3.2 * u)))
            bar_box = (int(round(56.0 * sx + pdx)), int(round(586.0 * sy + pdy)))
            bar_img = Image.new("RGBA", (bar_w, bar_h), (225, 204, 154, int(round(255 * portrait_alpha))))
            frame.alpha_composite(bar_img, bar_box)

        a_p = int(round(255 * portrait_alpha))
        draw_tracked_text(
            frame, cfg["person"]["name"], res["fonts"]["name"],
            (255, 255, 255, a_p), 72.0 * sx + pdx, 585.0 * sy + pdy, tracking=1.5 * u,
            shadow_rgba=(0, 0, 0, int(round(140 * portrait_alpha))), shadow_blur=6 * u, shadow_offset_y=2 * u,
        )

        # Fading hairline divider below name
        div_w = max(2, int(round(250.0 * sx * bar_rev)))
        div_x = np.linspace(1.0, 0.0, div_w, dtype=np.float32)[None, :]
        div_arr = np.zeros((max(1, int(round(1.5 * sy))), div_w, 4), dtype=np.uint8)
        div_arr[:, :, 0], div_arr[:, :, 1], div_arr[:, :, 2] = 232, 217, 181
        div_arr[:, :, 3] = np.clip(div_x * 0.48 * portrait_alpha * 255.0, 0, 255).astype(np.uint8)
        frame.alpha_composite(Image.fromarray(div_arr, mode="RGBA"), (int(round(72.0 * sx + pdx)), int(round(635.0 * sy + pdy))))

        draw_tracked_text(
            frame, cfg["person"]["title"], res["fonts"]["role"],
            (*sub_rgb, a_p), 72.0 * sx + pdx, 646.0 * sy + pdy, tracking=0.6 * u,
            shadow_rgba=(0, 0, 0, int(round(115 * portrait_alpha))), shadow_blur=5 * u, shadow_offset_y=2 * u,
        )

    # Layer 6: Right-Side 3D Specialty Icons
    slots3 = [(924.0, 114.0, 0.64, 0.96, 0.0), (1066.0, 234.0, 0.74, 1.06, 2.1), (1198.0, 366.0, 0.84, 1.16, 4.2)]
    slots2 = [(955.0, 150.0, 0.64, 0.96, 0.0), (1140.0, 310.0, 0.78, 1.10, 2.4)]
    discs = res["disciplines"]
    slots = slots2 if len(discs) == 2 else slots3

    for idx, disc in enumerate(discs):
        base_cx, base_cy, in_start, in_end, phase = slots[idx]
        if t < in_start:
            continue
        if t < in_end:
            p_raw = progress(t, in_start, in_end)
            alpha = ease_out_cubic(p_raw)
            scale = lerp(0.72, 1.0, ease_out_back(p_raw, 1.15))
            dy_anim = lerp(18.0 * sy, 0.0, ease_out_quart(p_raw))
        else:
            alpha, scale, dy_anim = 1.0, 1.0, 0.0
        if alpha <= 0.005:
            continue

        float_blend = ease_out_cubic(progress(t, in_end, in_end + 0.40))
        float_y = math.sin((t - in_start) * 1.9 + phase) * 2.5 * sy * float_blend
        cx = base_cx * sx
        cy = base_cy * sy + dy_anim + float_y

        icon_sz = max(4, int(round(114.0 * u * scale)))
        ic_res = disc["img"].resize((icon_sz, icon_sz), Image.Resampling.BILINEAR)
        if alpha < 0.999:
            ia = np.array(ic_res, dtype=np.float32)
            ia[:, :, 3] *= alpha
            ic_res = Image.fromarray(ia.astype(np.uint8), mode="RGBA")
        frame.alpha_composite(ic_res, (int(round(cx - icon_sz * 0.5)), int(round(cy - icon_sz * 0.5))))

        a_ic = int(round(255 * alpha))
        draw_tracked_text(
            frame, disc["name"], res["fonts"]["label"],
            (240, 246, 255, a_ic), cx, base_cy * sy + 60.0 * sy + dy_anim + float_y * 0.35,
            tracking=1.2 * u, align="center",
            shadow_rgba=(0, 0, 0, int(round(158 * alpha))), shadow_blur=6 * u, shadow_offset_y=2 * u,
        )

    # Layer 7: Bottom-Right Motto
    p_motto_move = ease_out_quart(progress(t, 0.78, 1.12))
    motto_alpha = ease_out_cubic(progress(t, 0.78, 1.05))
    if motto_alpha > 0.005:
        mdy = lerp(20.0 * sy, 0.0, p_motto_move)
        a_m = int(round(255 * motto_alpha))
        lines = cfg["motto"]["lines"][:2]
        tag_text = cfg["motto"].get("label", "校 训")
        tag_y = (592.0 if len(lines) == 1 else 558.0) * sy + mdy
        draw_tracked_text(
            frame, tag_text, res["fonts"]["motto_tag"],
            (222, 203, 160, a_m), (motto_x + 2.0) * sx, tag_y, tracking=4.0 * u,
            shadow_rgba=(0, 0, 0, int(round(178 * motto_alpha))), shadow_blur=5 * u, shadow_offset_y=2 * u,
        )
        for i, line_txt in enumerate(lines):
            ly = (622.0 if len(lines) == 1 else 585.0 + i * 48.0) * sy + mdy
            draw_tracked_text(
                frame, line_txt, res["fonts"]["motto_main"],
                (248, 250, 255, a_m), motto_x * sx, ly, tracking=5.5 * u,
                shadow_rgba=(0, 0, 0, int(round(190 * motto_alpha))), shadow_blur=8 * u, shadow_offset_y=3 * u,
            )

    return frame.convert("RGB")


def main():
    parser = argparse.ArgumentParser(description="Cross-platform Pillow + FFmpeg showcase video renderer.")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--preview-only", action="store_true", help="Only generate preview PNGs without invoking ffmpeg")
    args = parser.parse_args()

    cfg_path = os.path.abspath(args.config)
    base_dir = os.path.dirname(cfg_path)
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    vid = cfg.get("video", {})
    W = int(vid.get("width", 1332))
    H = int(vid.get("height", 720))
    FPS = int(vid.get("fps", 40))
    DURATION = float(vid.get("duration", 4.80))
    TOTAL_FRAMES = int(round(DURATION * FPS))
    u = min(W / 1332.0, H / 720.0)
    sx, sy = W / 1332.0, H / 720.0

    pal = cfg["palette"]
    ribbon_rgb = hex_to_rgb(pal.get("ribbon_color", pal["bg_bottom"]))

    discs = []
    for d in cfg["disciplines"][:3]:
        discs.append({"name": d["name"], "img": Image.open(resolve_path(base_dir, d["icon"])).convert("RGBA")})

    res = {
        "cfg": cfg,
        "W": W,
        "H": H,
        "DURATION": DURATION,
        "bg_base": build_background_base(W, H, pal),
        "particles": make_particles(W, H),
        "gold_grad": make_gold_gradient(W, H),
        "ribbon_img": make_ribbon_image(max(40, int(round(444 * sx))), max(20, int(round(106 * sy))), ribbon_rgb),
        "emblem": Image.open(resolve_path(base_dir, cfg["assets"]["emblem"])).convert("RGBA"),
        "campus": Image.open(resolve_path(base_dir, cfg["assets"]["campus"])).convert("RGB"),
        "portrait": Image.open(resolve_path(base_dir, cfg["assets"]["portrait"])).convert("RGBA"),
        "disciplines": discs,
        "fonts": load_fonts(cfg, u),
    }

    previews_dir = resolve_path(base_dir, cfg.get("previews_dir", "previews"))
    os.makedirs(previews_dir, exist_ok=True)

    preview_map = {
        int(round(0.20 * FPS)): "preview_t020.png",
        int(round(0.45 * FPS)): "preview_t045.png",
        int(round(0.65 * FPS)): "preview_t065.png",
        int(round(0.85 * FPS)): "preview_t085.png",
        int(round(1.30 * FPS)): "preview_t130.png",
        min(TOTAL_FRAMES - 1, int(round(3.00 * FPS))): "preview_t300.png",
    }

    if args.preview_only:
        for idx, fname in preview_map.items():
            t = idx / float(FPS)
            img = render_frame(res, t)
            out_p = os.path.join(previews_dir, fname)
            img.save(out_p)
            print(f"Saved preview: {out_p} at t={t:.2f}s")
        return

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        print("Error: ffmpeg not found in PATH. Install ffmpeg or run on macOS with render_video.swift.", file=sys.stderr)
        sys.exit(1)

    output_path = resolve_path(base_dir, vid.get("output", "output.mp4"))
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    cmd = [
        ffmpeg_bin, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}",
        "-r", str(FPS),
        "-i", "-",
        "-an",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "16",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for frame_idx in range(TOTAL_FRAMES):
            t = frame_idx / float(FPS)
            img = render_frame(res, t)
            if frame_idx in preview_map:
                out_p = os.path.join(previews_dir, preview_map[frame_idx])
                img.save(out_p)
                print(f"Saved preview: {out_p} at t={t:.2f}s")
            proc.stdin.write(img.tobytes())
        proc.stdin.close()
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"ffmpeg exited with code {ret}")
    except Exception:
        proc.kill()
        raise

    print(f"Successfully rendered {output_path} ({TOTAL_FRAMES} frames @ {FPS}fps, {DURATION}s, 0 audio tracks)")


if __name__ == "__main__":
    main()
