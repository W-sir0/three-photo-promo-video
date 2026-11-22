---
name: university-showcase-video
description: >-
  Creates an emblem-first, beat-style university showcase MP4 animation from just 3 user-provided photos
  (university emblem, campus landmark, and representative scholar/founder). Use when the user asks to
  generate a university showcase video, academic intro animation, or emblem-centered profile motion graphic
  using three input images.
---

# University Showcase Video

Creates a studio-grade, silent (`0` audio tracks) MP4 showcase animation from **3 photos**:
1. **School emblem** (校徽)
2. **Campus landmark** (校园标志性建筑)
3. **Representative figure** (代表人物/校长/院士)

The animation uses an **emblem-first reveal**: the circular emblem appears centered over a hue-locked textured backdrop (`0.00s–0.48s`), rises to the apex while pulling open a champagne-gold triangle framing the campus landmark (`0.48s–0.96s`), and triggers a staggered entrance for the bilingual university name, 3/4 portrait with fading nameplate, 3 sculpted 3D discipline icons, and school motto (`0.62s–1.16s`).

---

## Workflow

### Phase 1: Input Intake & Human Confirmation Gate
1. Inspect the 3 uploaded photos to identify the university, landmark, and representative figure.
2. Run web search to verify:
   - Official Chinese & English university name
   - Official school motto (split cleanly into 1 or 2 balanced lines)
   - Representative figure's accurate name & concise title (e.g., `著名教育家  ·  吉林大学原校长` or `中国工程院院士  ·  菌物学家`)
   - Top **3 flagship disciplines** suitable for visual 3D sculpture icons
3. Extract the exact hue-locked palette from the emblem:
   ```bash
   python3 ./scripts/extract_palette.py <emblem_path> --update-config config.json
   ```
4. **Stop and ask the user to confirm** the researched metadata (school names, motto, person name/title, 3 disciplines, and extracted theme color) before generating icons or rendering the video.

### Phase 2: Asset Generation & Preparation
1. **Generate 3 unified 3D discipline icons** using the matte warm pearl-ivory clay prompt templates in [icon_prompts.md](./references/icon_prompts.md) (or the local NumPy SDF fallback described there if image-generation quota is unavailable).
2. **Verify portrait angle & sharpness**:
   - Prefer a crisp high-resolution portrait in a **3/4 pose facing toward the center landmark (rightward)** with no distracting background or watermarks.
   - If the user's photo is blurry/scanned or faces outward, search official university archives for a cleaner photo, or refine/generate a 3/4 portrait (see [icon_prompts.md](./references/icon_prompts.md)).
   - On macOS, generate a neural person segmentation mask:
     ```bash
     swiftc -O ./scripts/segment_portrait.swift -o build/segment_portrait
     ./build/segment_portrait <portrait_src> assets/portrait_mask.png
     ```
     *(If Vision fails inside a restricted sandbox with `CVPixelBufferPool` error `-8`, run `build/segment_portrait` outside the sandbox.)*
3. Populate `config.json` following [config_schema.md](./references/config_schema.md) and [config.example.json](./examples/config.example.json), then prepare all cutouts & color-graded images:
   ```bash
   python3 ./scripts/prep_assets.py --config config.json
   ```
4. **Inspect `previews/assets_check.png`** visually before rendering: verify clean hair/shoulder cutouts, zero watermarks, harmonized colors, and matched 3D icon style.

### Phase 3: Compile & Render MP4
- **macOS (primary native path, zero video-tool dependencies)**:
  ```bash
  swiftc -O ./scripts/render_video.swift -o build/render_video
  ./build/render_video --config config.json
  ```
  *(If `AVAssetWriter` hardware H.264 encoding is blocked inside a terminal sandbox with error `-11834`, re-run `build/render_video --config config.json` outside the sandbox.)*
- **Linux / Windows (cross-platform FFmpeg path)**:
  ```bash
  python3 ./scripts/render_video_ffmpeg.py --config config.json
  ```

### Phase 4: Visual & Technical Verification
Follow [design_checklist.md](./references/design_checklist.md):
1. Inspect `previews/preview_t045.png` (center emblem alone), `previews/preview_t065.png` (rising triangle), and `previews/preview_t130.png` (settled full frame).
2. Verify background hue matches `palette.hue_deg` within `±2°`, motto text is legible over the dark scrim, no watermarks or overlapping landmarks remain, and the MP4 matches `1332×720`, `40 fps`, `~4.8s`, `0` audio tracks.
