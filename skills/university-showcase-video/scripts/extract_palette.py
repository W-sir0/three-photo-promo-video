#!/usr/bin/env python3
"""Extract exact dominant hue from a university emblem and derive a hue-locked dark prestige palette."""

import argparse
import colorsys
import json
import math
import os
import sys
import numpy as np
from PIL import Image


def hsl_to_hex(h_deg: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb((h_deg % 360.0) / 360.0, np.clip(l, 0.0, 1.0), np.clip(s, 0.0, 1.0))
    return f"#{int(round(r * 255)):02X}{int(round(g * 255)):02X}{int(round(b * 255)):02X}"


def extract_palette(emblem_path: str) -> dict:
    img = Image.open(emblem_path).convert("RGBA")
    arr = np.array(img, dtype=np.float32)

    # Ignore transparent pixels if PNG has alpha
    alpha_ok = arr[:, :, 3] > 128 if arr.shape[2] == 4 else np.ones(arr.shape[:2], dtype=bool)
    rgb = arr[:, :, :3] / 255.0

    # Filter out white paper background and pure black pixels
    sum_rgb = rgb.sum(axis=2)
    non_white = alpha_ok & (~((rgb[:, :, 0] > 0.78) & (rgb[:, :, 1] > 0.78) & (rgb[:, :, 2] > 0.78))) & (sum_rgb < 2.35) & (sum_rgb > 0.16)

    pts = rgb[non_white]
    if len(pts) < 20:
        # Monochrome/grayscale emblem fallback: dignified slate + champagne gold
        h_deg, s_med, l_med = 210.0, 0.16, 0.30
        emblem_hex = "#36454F"
    else:
        hls = np.array([colorsys.rgb_to_hls(r, g, b) for r, g, b in pts], dtype=np.float32)
        h_arr = hls[:, 0] * 360.0
        l_arr = hls[:, 1]
        s_arr = hls[:, 2]

        chromatic = (s_arr >= 0.14) & (l_arr >= 0.08) & (l_arr <= 0.86)
        if np.sum(chromatic) >= max(20, int(0.12 * len(pts))):
            ch_h = h_arr[chromatic]
            ch_s = s_arr[chromatic]
            ch_l = l_arr[chromatic]
            ch_rgb = pts[chromatic]

            # Circular median hue
            ang = np.deg2rad(ch_h)
            mean_ang = math.atan2(float(np.median(np.sin(ang))), float(np.median(np.cos(ang))))
            h_deg = (math.degrees(mean_ang) + 360.0) % 360.0

            # Restrict to pixels within +/-25 deg of dominant hue so secondary accents don't skew median
            dh = np.abs(((ch_h - h_deg + 180.0) % 360.0) - 180.0)
            core = dh <= 25.0
            if np.any(core):
                h_deg = float(np.median(ch_h[core])) if float(np.ptp(ch_h[core])) < 60.0 else h_deg
                s_med = float(np.median(ch_s[core]))
                l_med = float(np.median(ch_l[core]))
                med_rgb = np.median(ch_rgb[core], axis=0)
            else:
                s_med = float(np.median(ch_s))
                l_med = float(np.median(ch_l))
                med_rgb = np.median(ch_rgb, axis=0)

            emblem_hex = f"#{int(round(med_rgb[0]*255)):02X}{int(round(med_rgb[1]*255)):02X}{int(round(med_rgb[2]*255)):02X}"
        else:
            h_deg, s_med, l_med = 210.0, 0.16, 0.30
            med_rgb = np.median(pts, axis=0)
            emblem_hex = f"#{int(round(med_rgb[0]*255)):02X}{int(round(med_rgb[1]*255)):02X}{int(round(med_rgb[2]*255)):02X}"

    # Calibrated hue-locked 4-tier dark prestige palette
    # Saturation moderated cleanly for both muted colors (e.g. #396770, S=0.33) and vivid colors (e.g. #0936BE, S=0.91)
    s_center = min(max(s_med * 0.96, 0.28), 0.76)
    s_mid = min(max(s_med * 1.03, 0.33), 0.79)
    s_outer = min(max(s_med * 1.14, 0.36), 0.82)
    s_bottom = min(max(s_med * 1.20, 0.38), 0.82)

    palette = {
        "hue_deg": round(h_deg, 1),
        "emblem_accent": emblem_hex,
        "bg_center": hsl_to_hex(h_deg, s_center, 0.38),
        "bg_mid": hsl_to_hex(h_deg, s_mid, 0.30),
        "bg_outer": hsl_to_hex(h_deg, s_outer, 0.19),
        "bg_bottom": hsl_to_hex(h_deg, s_bottom, 0.13),
        "scrim_color": hsl_to_hex(h_deg, min(s_outer, 0.78), 0.08),
        "ribbon_color": hsl_to_hex(h_deg, min(s_outer, 0.78), 0.09),
        "shadow_tint": hsl_to_hex(h_deg, min(max(s_med, 0.34), 0.78), 0.21),
        "halo_tint": hsl_to_hex(h_deg, min(s_center, 0.65), 0.60),
        "subtitle_color": hsl_to_hex(h_deg, min(max(s_med * 0.45, 0.22), 0.48), 0.85),
    }
    return palette


def main():
    parser = argparse.ArgumentParser(description="Extract hue-locked showcase video palette from a university emblem.")
    parser.add_argument("emblem", help="Path to emblem image (JPG/PNG)")
    parser.add_argument("--update-config", dest="config_path", help="Optional config.json path to update in place")
    args = parser.parse_args()

    palette = extract_palette(args.emblem)

    if args.config_path:
        cfg = {}
        if os.path.exists(args.config_path):
            with open(args.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        cfg["palette"] = palette
        with open(args.config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Updated palette in {args.config_path}", file=sys.stderr)

    print(json.dumps(palette, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
