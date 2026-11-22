# `config.json` Schema & Layout Reference

All relative paths in `config.json` are resolved relative to the directory containing `config.json`.

## Top-Level Structure

| Key | Required | Description |
| :--- | :--- | :--- |
| `university` | Yes | `{"name": "吉林大学", "english_name": "Jilin University"}` |
| `person` | Yes | `{"name": "匡亚明", "title": "著名教育家  ·  吉林大学原校长"}` |
| `motto` | Yes | `{"label": "校 训", "lines": ["求实创新", "励志图强"]}` (`lines` supports 1 or 2 items) |
| `disciplines` | Yes | Array of 2 or 3 objects: `{"name": "...", "raw_icon": "...", "icon": "..."}` |
| `raw_inputs` | Yes (for `prep_assets.py`) | `{"emblem": "...", "campus": "...", "portrait": "...", "portrait_mask": "(optional)"}` |
| `assets` | Yes | Output/ready PNG paths: `{"emblem": "...", "campus": "...", "portrait": "..."}` |
| `palette` | Yes | Generated automatically by `extract_palette.py --update-config config.json` |
| `campus_options` | No | Landmark preprocessing options (see below) |
| `portrait_options` | No | Portrait preprocessing options (see below) |
| `layout` | No | Fine-grained canvas positioning overrides (see below) |
| `video` | No | Output encoding settings (`width`, `height`, `fps`, `duration`, `output`) |
| `previews_dir` | No | Directory for `assets_check.png` and rendered frame previews (default `"previews"`) |
| `fonts` | No | Optional font path/index overrides for `render_video_ffmpeg.py` |

---

## Optional Tuning Blocks

### `campus_options`
- `auto_symmetry_crop` (`bool`, default `true`): Automatically centers symmetrical landmark facades horizontally.
- `trim_bottom_px` (`int`, default `0`): Trims plain foreground sidewalk/pavement at the bottom before scaling.
- `sky_extend` (`"auto"` | `bool`, default `"auto"`): When `"auto"` and source width/height `> 2.0`, extends sky smoothly upward with progressive 1D smoothing so panoramic buildings sit below the apex emblem without clipping.
- `crop_box` (`[x0, y0, x1, y1]`, optional): Explicit crop box (normalized `0..1` if all `<= 1.0`, otherwise pixel coords).

### `portrait_options`
- `crop_box` (`[x0, y0, x1, y1]`, optional): Applied before horizontal flip (useful to trim archive watermarks or outstretched arms/tables).
- `flip_horizontal` (`bool`, default `false`): Set `true` when the original photo faces left so the figure faces inward toward the center campus landmark.
- `restore_vintage` (`bool`, default `false`): Light median denoise (`35%` blend) for scanned vintage print photos.
- `sharpen` (`bool`, default `true`): Gentle unsharp mask for crisp edges.
- `edge_taper` (`bool`, default `true`): Smoothly tapers outer lower sleeve pixels touching left/right crop boundaries so no hard vertical edge appears.

### `layout` (in `1332×720` base coordinate space)
- `motto_x` (`number`, default `820`): Shift right (e.g., `835`–`850`) if a central campus stone inscription sits near `x = 700..820`.
- `portrait_x` (`number`, default `236`): Horizontal center of the bottom-left portrait.
- `portrait_height` (`number`, default `450`): Rendered portrait height (native aspect ratio is always preserved).
- `campus_y` (`number`, default `448`): Vertical center of the campus landmark inside the triangle.

### `video`
- `width` (`int`, default `1332`)
- `height` (`int`, default `720`)
- `fps` (`int`, default `40`)
- `duration` (`number`, default `4.80`)
- `output` (`string`, default `"output.mp4"`)
