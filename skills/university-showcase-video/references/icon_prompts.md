# 3D Discipline Icon & Portrait Refinement Prompts

Keep all 3 discipline icons strictly unified in material, lighting, camera angle, and background so they read as a cohesive sculptural set.

---

## 1. Unified 3D Discipline Icon Prompt Template (1:1 Square)

Use this template for each of the 3 disciplines, substituting only `<SUBJECT_DESCRIPTION>`:

```text
Generate a single square 1:1 3D miniature icon image.

Subject: <SUBJECT_DESCRIPTION>

Style & Composition requirements (CRITICAL):
- Isometric 3/4 view, smooth matte warm pearl-ivory / alabaster clay 3D miniature sculpture (refined matte porcelain / studio clay miniature) with subtle warm champagne-gold rim lighting and crisp sculptural detail.
- Floating cleanly centered with generous margin (~20% margin on all sides) on a PURE SOLID FLAT BLACK (#000000) background.
- Strictly NO ground plane, NO floor, NO cast shadow on any surface, NO pedestal, NO circular base, NO frame, NO text, NO letters, NO watermark.
- High-resolution square 1:1 aspect ratio.
```

### Example `<SUBJECT_DESCRIPTION>` Ideas by Discipline
- **化学 / Chemistry**: `A sculptural 3D hexagonal molecular lattice and orbital bond structure gracefully intertwined with a stylized laboratory Erlenmeyer flask, refined scientific miniature model feel.`
- **车辆工程 / Vehicle Engineering**: `A sleek sculptural 3D aerodynamic modern concept sedan / automotive engineering model with crisp sculpted body lines, sculpted wheels, and clean wind-tunnel contour elegance.`
- **考古学 / Archaeology**: `An ornate ancient Chinese bronze ding tripod vessel miniature sculpture with refined classical relief patterns, upright twin ear handles, and three sturdy sculpted legs.`
- **菌物学 / Mycology**: `A sculptural 3D cluster of lingzhi (reishi) mushrooms and layered shiitake/oyster mushrooms with delicate organic gills and subtle bioluminescent warm-ivory sheen.`
- **作物学 / Crop Science**: `A sculptural 3D artistic bundle of plump wheat/rice grain ears and a corn cob with sweeping stylized leaves, refined architectural miniature model feel.`
- **计算机 / AI / Information Tech**: `A sculptural 3D microchip processor wafer with delicate isometric circuit traces and glowing warm champagne-ivory core pins.`
- **法学 / Law**: `A sculptural 3D balanced classical scales of justice resting lightly with an open sculpted legal tome and minimal gavel accent.`
- **临床医学 / Medicine**: `A sculptural 3D double-helix medical cadence/stethoscope and anatomical heart or caduceus miniature sculpture with crisp porcelain surfaces.`

---

## 2. Local Offline Fallback (Zero Image-API Dependency)

If an image generation API hits quota limits or is unavailable, render procedural 3D SDF sculptures in Python + NumPy using:
- Base albedo `#EFE3CC` (warm pearl-ivory)
- Upper-left-front warm studio key light + 5-step SDF ambient occlusion + soft raymarched self-shadowing
- Champagne-gold Fresnel rim light (`#FFE3AE`) from upper-right-back
- Direct RGBA output on transparent background, supersampled (`960×960` → tight crop → centered into `320×320` with `target_span = 264`).

---

## 3. 3/4 Portrait Generation / Refinement Prompt (When Source Photo Is Straight-On or Low-Res)

If the user's figure photo is strictly straight front-facing or too cluttered to cleanly isolate, generate a clean 3:4 studio portrait referencing the original photo:

```text
Edit/generate a formal chest-up studio portrait based closely on the reference portrait at <REF_PORTRAIT_PATH>.

CRITICAL REQUIREMENTS:
1. Preserve the EXACT authentic facial likeness, age, facial structure, hairline, glasses (if any), attire, and dignified expression of the person in the reference photo.
2. Pose & Direction: Natural 3/4 angled side-turned chest-up studio portrait facing toward the viewer's RIGHT (torso angled ~35 degrees right, head turned ~25 degrees right, looking calmly toward the right — NOT straight front-facing). Ensure full shoulders extend cleanly to the bottom edge.
3. Background: Completely flat, uniform, solid light-gray (#E6E6E6) studio background with soft even studio lighting. Strictly NO shadows, NO gradients, NO text, NO watermark.
4. Aspect ratio: 3:4 portrait.
```
