# Visual & Technical QA Checklist

Verify every item below before delivering the final MP4.

## 1. Asset Sheet Check (`previews/assets_check.png`)
- **Portrait cutout**:
  - Zero bright/brown background halos around hair, ears, glasses, or shoulders.
  - Enclosed interior clothing (white collar, tie) is completely intact.
  - Zero museum/archive watermarks remaining at the bottom edge.
  - Figure faces slightly **rightward** (inward toward the campus landmark) rather than away from the composition or rigidly straight-on.
  - Outer sleeves taper smoothly with zero horizontal notch or hard rectangular cut.
- **Emblem**: Clean circular disc with no stray white outer margin or jagged teeth.
- **Campus landmark**: Symmetrically centered; overly neon lawn greens are tamed; any extended upper sky has zero vertical streaks.
- **3D discipline icons**: All 3 share the exact same matte warm pearl-ivory clay material, champagne-gold rim lighting, and crisp transparent cutouts with zero dark edges.

## 2. Keyframe Verification (`preview_t045`, `preview_t065`, `preview_t130`)
- **Hue lock (`preview_t045` / `preview_t130`)**: Sampled background corners and upper-center glow stay within `±2°` of `palette.hue_deg` (the emblem's hue).
- **Emblem-first opening (`preview_t045`)**: At `t = 0.45s`, ONLY the textured theme backdrop, subtle bokeh specks, and centered circular emblem (`r = 116` scaled) are visible — zero premature triangle, title, portrait, icons, or motto.
- **Smooth expansion (`preview_t065`)**: Emblem rises smoothly while pulling open the champagne-gold triangle; inner hairline and radial dark scrim render cleanly without artifacts.
- **Final settled hero frame (`preview_t130`)**:
  - Upper-left title (`name` / `english_name`) has clean clearance above the portrait's head.
  - Lower-left fading ribbon (`ribbon_color`) is smooth left-to-right with no boxy border.
  - Right-side 3D icons sit cleanly outside the triangle slope with generous spacing from the apex emblem.
  - Bottom-right motto has high contrast over the dark scrim and does not clash awkwardly with prominent landmark signage.

## 3. Output MP4 Specs
- Resolution matches `1332 × 720` (or configured `width × height`)
- Frame rate matches `40 fps`
- Duration matches `~4.80s`
- `audioTracks = 0` (completely silent)
