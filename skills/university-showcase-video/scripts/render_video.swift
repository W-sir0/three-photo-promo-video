import Foundation
import CoreGraphics
import CoreText
import ImageIO
import AVFoundation
import CoreVideo

// MARK: - Config Schema

struct VideoConfig: Codable {
    struct UniversityInfo: Codable {
        let name: String
        let english_name: String
    }
    struct PersonInfo: Codable {
        let name: String
        let title: String
    }
    struct MottoInfo: Codable {
        let label: String?
        let lines: [String]
    }
    struct DisciplineItem: Codable {
        let name: String
        let icon: String
    }
    struct AssetsPaths: Codable {
        let emblem: String
        let campus: String
        let portrait: String
    }
    struct PaletteConfig: Codable {
        let emblem_accent: String
        let bg_center: String
        let bg_mid: String
        let bg_outer: String
        let bg_bottom: String
        let scrim_color: String?
        let ribbon_color: String?
        let halo_tint: String?
        let subtitle_color: String?
    }
    struct LayoutConfig: Codable {
        let motto_x: Double?
        let portrait_x: Double?
        let portrait_height: Double?
        let campus_y: Double?
    }
    struct VideoSettings: Codable {
        let width: Int?
        let height: Int?
        let fps: Int32?
        let duration: Double?
        let output: String?
    }

    let university: UniversityInfo
    let person: PersonInfo
    let motto: MottoInfo
    let disciplines: [DisciplineItem]
    let assets: AssetsPaths
    let palette: PaletteConfig
    let layout: LayoutConfig?
    let video: VideoSettings?
    let previews_dir: String?
}

// MARK: - CLI & Path Resolution

func parseConfigArg() -> String {
    let args = CommandLine.arguments
    for i in 1..<args.count {
        if args[i] == "--config", i + 1 < args.count {
            return args[i + 1]
        }
    }
    fputs("Usage: render_video --config <config.json>\n", stderr)
    exit(1)
}

func resolvePath(_ baseDir: URL, _ path: String) -> String {
    if path.hasPrefix("/") {
        return path
    }
    return baseDir.appendingPathComponent(path).standardized.path
}

// MARK: - Math & Easing Helpers

@inline(__always)
func clamp(_ x: Double, _ a: Double, _ b: Double) -> Double {
    return min(max(x, a), b)
}

@inline(__always)
func lerp(_ a: Double, _ b: Double, _ t: Double) -> Double {
    return a + (b - a) * t
}

@inline(__always)
func progress(_ t: Double, _ start: Double, _ end: Double) -> Double {
    if end <= start { return t >= end ? 1.0 : 0.0 }
    return clamp((t - start) / (end - start), 0.0, 1.0)
}

@inline(__always)
func easeInOutCubic(_ t: Double) -> Double {
    let x = clamp(t, 0.0, 1.0)
    return x < 0.5 ? 4.0 * x * x * x : 1.0 - pow(-2.0 * x + 2.0, 3.0) / 2.0
}

@inline(__always)
func easeOutQuart(_ t: Double) -> Double {
    let x = clamp(t, 0.0, 1.0)
    return 1.0 - pow(1.0 - x, 4.0)
}

@inline(__always)
func easeOutCubic(_ t: Double) -> Double {
    let x = clamp(t, 0.0, 1.0)
    return 1.0 - pow(1.0 - x, 3.0)
}

@inline(__always)
func easeOutBack(_ t: Double, overshoot: Double = 1.25) -> Double {
    let x = clamp(t, 0.0, 1.0)
    let c1 = overshoot
    let c3 = c1 + 1.0
    return 1.0 + c3 * pow(x - 1.0, 3.0) + c1 * pow(x - 1.0, 2.0)
}

// MARK: - Color, Image & Text Helpers

let srgb = CGColorSpace(name: CGColorSpace.sRGB)!

struct RGBTuple {
    let r: Int
    let g: Int
    let b: Int
}

func parseHex(_ hex: String) -> RGBTuple {
    let cleaned = hex.trimmingCharacters(in: .whitespacesAndNewlines).replacingOccurrences(of: "#", with: "")
    guard cleaned.count == 6, let val = UInt32(cleaned, radix: 16) else {
        return RGBTuple(r: 20, g: 50, b: 100)
    }
    return RGBTuple(
        r: Int((val >> 16) & 0xFF),
        g: Int((val >> 8) & 0xFF),
        b: Int(val & 0xFF)
    )
}

func rgbaColor(_ r: Int, _ g: Int, _ b: Int, _ a: Double = 1.0) -> CGColor {
    return CGColor(
        colorSpace: srgb,
        components: [CGFloat(r) / 255.0, CGFloat(g) / 255.0, CGFloat(b) / 255.0, CGFloat(a)]
    )!
}

func hexColor(_ hex: String, _ a: Double = 1.0) -> CGColor {
    let c = parseHex(hex)
    return rgbaColor(c.r, c.g, c.b, a)
}

func loadCGImage(_ path: String) -> CGImage {
    let url = URL(fileURLWithPath: path)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        fatalError("Failed to load image: \(path)")
    }
    return img
}

func savePNG(_ cgImage: CGImage, to path: String) {
    let url = URL(fileURLWithPath: path)
    try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    guard let dst = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil) else {
        fatalError("Failed to create PNG destination: \(path)")
    }
    CGImageDestinationAddImage(dst, cgImage, nil)
    if !CGImageDestinationFinalize(dst) {
        fatalError("Failed to write PNG: \(path)")
    }
}

func drawImageTopDown(_ ctx: CGContext, _ img: CGImage, in rect: CGRect) {
    ctx.saveGState()
    ctx.translateBy(x: rect.minX, y: rect.maxY)
    ctx.scaleBy(x: 1.0, y: -1.0)
    ctx.draw(img, in: CGRect(x: 0, y: 0, width: rect.width, height: rect.height))
    ctx.restoreGState()
}

func makeFont(_ psName: String, size: CGFloat) -> CTFont {
    let font = CTFontCreateWithName(psName as CFString, size, nil)
    let resolved = CTFontCopyPostScriptName(font) as String
    if resolved != psName {
        fputs("Notice: requested font \(psName) resolved as \(resolved)\n", stderr)
    }
    return font
}

enum TextAlign {
    case left
    case center
}

func drawTextTopDown(
    _ ctx: CGContext,
    _ text: String,
    font: CTFont,
    color: CGColor,
    x: CGFloat,
    topY: CGFloat,
    tracking: CGFloat = 0.0,
    align: TextAlign = .left,
    shadowColor: CGColor? = nil,
    shadowBlur: CGFloat = 0.0,
    shadowOffsetY: CGFloat = 2.0
) {
    let attrs: [NSAttributedString.Key: Any] = [
        NSAttributedString.Key(kCTFontAttributeName as String): font,
        NSAttributedString.Key(kCTForegroundColorAttributeName as String): color,
        NSAttributedString.Key(kCTKernAttributeName as String): tracking
    ]
    let attrStr = NSAttributedString(string: text, attributes: attrs)
    let line = CTLineCreateWithAttributedString(attrStr)

    var ascent: CGFloat = 0
    var descent: CGFloat = 0
    var leading: CGFloat = 0
    let width = CGFloat(CTLineGetTypographicBounds(line, &ascent, &descent, &leading))

    let drawX = (align == .center) ? (x - width / 2.0) : x
    let baselineY = topY + ascent * 0.88

    ctx.saveGState()
    if let sc = shadowColor {
        ctx.setShadow(offset: CGSize(width: 0, height: -shadowOffsetY), blur: shadowBlur, color: sc)
    }
    ctx.textMatrix = CGAffineTransform(scaleX: 1.0, y: -1.0)
    ctx.textPosition = CGPoint(x: drawX, y: baselineY)
    CTLineDraw(line, ctx)
    ctx.restoreGState()
}

// MARK: - Background Texture Builder

func buildBackgroundBase(width W: Int, height H: Int, palette: VideoConfig.PaletteConfig) -> CGImage {
    let sx = CGFloat(W) / 1332.0
    let sy = CGFloat(H) / 720.0
    let u = min(sx, sy)

    let ctx = CGContext(
        data: nil,
        width: W,
        height: H,
        bitsPerComponent: 8,
        bytesPerRow: W * 4,
        space: srgb,
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    )!

    ctx.translateBy(x: 0, y: CGFloat(H))
    ctx.scaleBy(x: 1.0, y: -1.0)

    ctx.setFillColor(hexColor(palette.bg_mid, 1.0))
    ctx.fill(CGRect(x: 0, y: 0, width: W, height: H))

    let radialColors = [
        hexColor(palette.bg_center, 1.0),
        hexColor(palette.bg_mid, 1.0),
        hexColor(palette.bg_outer, 1.0),
        hexColor(palette.bg_bottom, 1.0)
    ] as CFArray
    let radialLocs: [CGFloat] = [0.0, 0.36, 0.74, 1.0]
    let radialGrad = CGGradient(colorsSpace: srgb, colors: radialColors, locations: radialLocs)!
    ctx.drawRadialGradient(
        radialGrad,
        startCenter: CGPoint(x: 666.0 * sx, y: 205.0 * sy),
        startRadius: 0,
        endCenter: CGPoint(x: 666.0 * sx, y: 260.0 * sy),
        endRadius: 880.0 * u,
        options: [.drawsBeforeStartLocation, .drawsAfterEndLocation]
    )

    let bottomColors = [
        hexColor(palette.bg_bottom, 0.0),
        hexColor(palette.bg_bottom, 0.45),
        hexColor(palette.bg_bottom, 0.85)
    ] as CFArray
    let bottomGrad = CGGradient(colorsSpace: srgb, colors: bottomColors, locations: [0.0, 0.55, 1.0])!
    ctx.drawLinearGradient(
        bottomGrad,
        start: CGPoint(x: 0, y: 480.0 * sy),
        end: CGPoint(x: 0, y: CGFloat(H)),
        options: []
    )

    ctx.saveGState()
    let beamColors = [
        rgbaColor(210, 228, 250, 0.0),
        rgbaColor(210, 228, 250, 0.032),
        rgbaColor(210, 228, 250, 0.0)
    ] as CFArray
    let beamGrad = CGGradient(colorsSpace: srgb, colors: beamColors, locations: [0.0, 0.5, 1.0])!
    ctx.drawLinearGradient(
        beamGrad,
        start: CGPoint(x: 180.0 * sx, y: 0),
        end: CGPoint(x: 560.0 * sx, y: 380.0 * sy),
        options: []
    )
    ctx.drawLinearGradient(
        beamGrad,
        start: CGPoint(x: 820.0 * sx, y: 0),
        end: CGPoint(x: 1260.0 * sx, y: 440.0 * sy),
        options: []
    )
    ctx.restoreGState()

    ctx.saveGState()
    let arcRadii: [CGFloat] = [132, 198, 286, 392, 520]
    for (idx, r) in arcRadii.enumerated() {
        ctx.setStrokeColor(rgbaColor(238, 224, 188, idx % 2 == 0 ? 0.045 : 0.026))
        ctx.setLineWidth((idx == 1 ? 1.2 : 0.9) * u)
        if idx % 2 == 1 {
            ctx.setLineDash(phase: 0, lengths: [10.0 * u, 14.0 * u])
        } else {
            ctx.setLineDash(phase: 0, lengths: [])
        }
        ctx.addArc(center: CGPoint(x: 666.0 * sx, y: 152.0 * sy), radius: r * u, startAngle: 0, endAngle: .pi * 2.0, clockwise: false)
        ctx.strokePath()
    }
    ctx.restoreGState()

    if let raw = ctx.data {
        let ptr = raw.bindMemory(to: UInt8.self, capacity: W * H * 4)
        var seed: UInt64 = 0x517cc1b727220a95
        for i in 0..<(W * H) {
            seed = seed &* 6364136223846793005 &+ 1442695040888963407
            let n = Int((seed >> 32) & 0xFF)
            let delta = (n * 11) / 255 - 5
            let off = i * 4
            ptr[off + 0] = UInt8(clamping: Int(ptr[off + 0]) + delta)
            ptr[off + 1] = UInt8(clamping: Int(ptr[off + 1]) + delta)
            ptr[off + 2] = UInt8(clamping: Int(ptr[off + 2]) + delta)
        }
    }

    return ctx.makeImage()!
}

// MARK: - Bokeh Dust Particles

struct Particle {
    let x0: Double
    let y0: Double
    let r: Double
    let speedY: Double
    let driftX: Double
    let phase: Double
    let alpha: Double
    let warm: Bool
}

func makeParticles(width W: Int, height H: Int) -> [Particle] {
    var list: [Particle] = []
    var seed: UInt64 = 0x9e3779b97f4a7c15
    func nextRand() -> Double {
        seed = seed &* 6364136223846793005 &+ 1442695040888963407
        return Double((seed >> 33) & 0x7FFFFFFF) / Double(0x7FFFFFFF)
    }
    let scale = Double(H) / 720.0
    for i in 0..<24 {
        list.append(Particle(
            x0: (40.0 + nextRand() * 1252.0) * (Double(W) / 1332.0),
            y0: (20.0 + nextRand() * 680.0) * scale,
            r: (1.4 + nextRand() * 2.8) * scale,
            speedY: (11.0 + nextRand() * 14.0) * scale,
            driftX: (6.0 + nextRand() * 10.0) * scale,
            phase: nextRand() * .pi * 2.0,
            alpha: 0.08 + nextRand() * 0.14,
            warm: i % 3 == 0
        ))
    }
    return list
}

// MARK: - Scene Resources

struct DisciplineRender {
    let name: String
    let img: CGImage
}

struct SceneResources {
    let W: Int
    let H: Int
    let FPS: Int32
    let DURATION: Double
    let config: VideoConfig
    let bgBase: CGImage
    let portrait: CGImage
    let emblem: CGImage
    let campus: CGImage
    let disciplines: [DisciplineRender]
    let particles: [Particle]

    let fontTitleCN: CTFont
    let fontTitleEN: CTFont
    let fontName: CTFont
    let fontRole: CTFont
    let fontLabel: CTFont
    let fontMottoTag: CTFont
    let fontMottoMain: CTFont
}

func loadResources(config: VideoConfig, baseDir: URL) -> SceneResources {
    let W = config.video?.width ?? 1332
    let H = config.video?.height ?? 720
    let FPS = config.video?.fps ?? 40
    let DURATION = config.video?.duration ?? 4.80
    let u = CGFloat(min(Double(W) / 1332.0, Double(H) / 720.0))

    let discs = config.disciplines.prefix(3).map { d in
        DisciplineRender(name: d.name, img: loadCGImage(resolvePath(baseDir, d.icon)))
    }

    return SceneResources(
        W: W,
        H: H,
        FPS: FPS,
        DURATION: DURATION,
        config: config,
        bgBase: buildBackgroundBase(width: W, height: H, palette: config.palette),
        portrait: loadCGImage(resolvePath(baseDir, config.assets.portrait)),
        emblem: loadCGImage(resolvePath(baseDir, config.assets.emblem)),
        campus: loadCGImage(resolvePath(baseDir, config.assets.campus)),
        disciplines: discs,
        particles: makeParticles(width: W, height: H),
        fontTitleCN: makeFont("STSongti-SC-Bold", size: 46 * u),
        fontTitleEN: makeFont("Georgia", size: 17 * u),
        fontName: makeFont("STSongti-SC-Bold", size: 36 * u),
        fontRole: makeFont("PingFangSC-Regular", size: 16.5 * u),
        fontLabel: makeFont("PingFangSC-Medium", size: 17 * u),
        fontMottoTag: makeFont("PingFangSC-Medium", size: 16 * u),
        fontMottoMain: makeFont("STSongti-SC-Bold", size: 37 * u)
    )
}

// MARK: - Frame Rendering

func drawDynamicTrianglePath(_ ctx: CGContext, apexX: CGFloat, apexY: CGFloat, bottomY: CGFloat, slope: CGFloat) {
    let halfW = max(1.0, (bottomY - apexY) * slope)
    ctx.beginPath()
    ctx.move(to: CGPoint(x: apexX, y: apexY))
    ctx.addLine(to: CGPoint(x: apexX + halfW, y: bottomY))
    ctx.addLine(to: CGPoint(x: apexX - halfW, y: bottomY))
    ctx.closePath()
}

func drawDynamicInnerTrianglePath(_ ctx: CGContext, apexX: CGFloat, apexY: CGFloat, bottomY: CGFloat, slope: CGFloat, scale: CGFloat) {
    let yTop = apexY + 9.0 * scale
    let yBot = bottomY - 6.0 * scale
    let halfW = max(1.0, (yBot - yTop) * slope)
    ctx.beginPath()
    ctx.move(to: CGPoint(x: apexX, y: yTop))
    ctx.addLine(to: CGPoint(x: apexX + halfW, y: yBot))
    ctx.addLine(to: CGPoint(x: apexX - halfW, y: yBot))
    ctx.closePath()
}

func renderFrame(into ctx: CGContext, res: SceneResources, t: Double) {
    let W = res.W
    let H = res.H
    let sx = Double(W) / 1332.0
    let sy = Double(H) / 720.0
    let u = min(sx, sy)
    let pal = res.config.palette
    let scrimHex = pal.scrim_color ?? pal.bg_bottom
    let ribbonHex = pal.ribbon_color ?? pal.bg_bottom
    let haloHex = pal.halo_tint ?? pal.bg_center
    let subHex = pal.subtitle_color ?? "#D4E1F5"

    ctx.saveGState()
    ctx.translateBy(x: 0, y: CGFloat(H))
    ctx.scaleBy(x: 1.0, y: -1.0)
    ctx.interpolationQuality = .high

    // -------------------------------------------------------------------------
    // Timeline Parameters (Emblem-First Reveal)
    // -------------------------------------------------------------------------
    let emblemAlpha = easeOutCubic(progress(t, 0.05, 0.34))
    let emblemIntroScale = lerp(0.76, 1.00, easeOutBack(progress(t, 0.05, 0.40), overshoot: 1.15))
    let ringSweep = easeOutCubic(progress(t, 0.08, 0.42))

    let pRise = easeInOutCubic(progress(t, 0.48, 0.96))
    let apexX = 666.0 * sx
    let emblemCenterY = lerp(360.0 * sy, 152.0 * sy, pRise)
    let baseOuterR = lerp(116.0 * u, 104.0 * u, pRise)
    let outerR = CGFloat(baseOuterR * emblemIntroScale)
    let bezelInnerR = outerR * (97.5 / 104.0)
    let emblemR = outerR * (94.5 / 104.0)

    let introHalo = sin(progress(t, 0.05, 0.48) * .pi) * 0.65
    let riseHalo = sin(pRise * .pi) * 0.70
    let haloPulse = max(introHalo, riseHalo)

    let triSlope = CGFloat((561.0 * sx) / (593.0 * sy))
    let triAlpha = t <= 0.48 ? 0.0 : easeOutCubic(progress(t, 0.48, 0.56))
    let dropT = easeOutQuart(progress(t, 0.48, 0.70))
    let triApexY = CGFloat(emblemCenterY)
    let triBottomY = CGFloat(lerp(emblemCenterY, 745.0 * sy, dropT))

    let gleam1 = (t >= 0.75 && t <= 1.30) ? progress(t, 0.75, 1.30) : -1.0
    let gleam2 = (t >= 2.80 && t <= 3.50) ? progress(t, 2.80, 3.50) : -1.0
    let activeGleam = gleam1 >= 0 ? gleam1 : gleam2

    let pTitle = easeOutCubic(progress(t, 0.62, 0.94))
    let titleAlpha = pTitle
    let titleDx = lerp(-18.0 * sx, 0.0, pTitle)

    let pPortMove = easeOutQuart(progress(t, 0.64, 1.00))
    let portraitAlpha = easeOutCubic(progress(t, 0.64, 0.92))
    let portraitDx = lerp(-16.0 * sx, 0.0, pPortMove)
    let portraitDy = lerp(24.0 * sy, 0.0, pPortMove)
    let barReveal = easeOutCubic(progress(t, 0.72, 1.04))

    let pMottoMove = easeOutQuart(progress(t, 0.78, 1.12))
    let mottoAlpha = easeOutCubic(progress(t, 0.78, 1.05))
    let mottoDy = lerp(20.0 * sy, 0.0, pMottoMove)

    // -------------------------------------------------------------------------
    // Layer 1: Background + Ambient Bokeh
    // -------------------------------------------------------------------------
    drawImageTopDown(ctx, res.bgBase, in: CGRect(x: 0, y: 0, width: W, height: H))

    for pt in res.particles {
        let y = (pt.y0 - pt.speedY * t).truncatingRemainder(dividingBy: Double(H))
        let wrappedY = y < 0 ? y + Double(H) : y
        let x = pt.x0 + sin(t * 0.9 + pt.phase) * pt.driftX
        let pulse = 0.72 + 0.28 * sin(t * 1.7 + pt.phase)
        let color = pt.warm
            ? rgbaColor(246, 232, 196, pt.alpha * pulse)
            : hexColor(subHex, pt.alpha * pulse)
        ctx.setFillColor(color)
        ctx.fillEllipse(in: CGRect(x: x - pt.r, y: wrappedY - pt.r, width: pt.r * 2.0, height: pt.r * 2.0))
    }

    if haloPulse > 0.01 {
        let hColors = [
            rgbaColor(242, 228, 188, 0.28 * haloPulse),
            hexColor(haloHex, 0.16 * haloPulse),
            hexColor(pal.bg_mid, 0.0)
        ] as CFArray
        let hGrad = CGGradient(colorsSpace: srgb, colors: hColors, locations: [0.0, 0.45, 1.0])!
        ctx.drawRadialGradient(
            hGrad,
            startCenter: CGPoint(x: apexX, y: emblemCenterY),
            startRadius: 0,
            endCenter: CGPoint(x: apexX, y: emblemCenterY),
            endRadius: 280.0 * u,
            options: [.drawsBeforeStartLocation]
        )
    }

    // -------------------------------------------------------------------------
    // Layer 2: Rising Golden Triangle + Campus Landmark + Bottom Scrim
    // -------------------------------------------------------------------------
    let mottoXBase = res.config.layout?.motto_x ?? 820.0
    if triAlpha > 0.005 && (triBottomY - triApexY) > 6.0 {
        let useGroupLayer = triAlpha < 0.999
        if useGroupLayer {
            ctx.saveGState()
            ctx.setAlpha(CGFloat(triAlpha))
            ctx.beginTransparencyLayer(auxiliaryInfo: nil)
        }

        ctx.saveGState()
        ctx.setShadow(offset: CGSize(width: 0, height: -4.0 * u), blur: 28.0 * u, color: hexColor(scrimHex, 0.58))
        drawDynamicTrianglePath(ctx, apexX: CGFloat(apexX), apexY: triApexY, bottomY: triBottomY, slope: triSlope)
        ctx.setFillColor(hexColor(pal.bg_bottom, 1.0))
        ctx.fillPath()
        ctx.restoreGState()

        ctx.saveGState()
        drawDynamicTrianglePath(ctx, apexX: CGFloat(apexX), apexY: triApexY, bottomY: triBottomY, slope: triSlope)
        ctx.clip()

        let kbProgress = progress(t, 0.48, res.DURATION)
        let kbScale = 1.0 + 0.048 * kbProgress
        let cAspect = Double(res.campus.width) / Double(res.campus.height)
        let campusW = 1140.0 * sx * kbScale
        let campusH = campusW / cAspect
        let targetCampusY = (res.config.layout?.campus_y ?? 448.0) * sy
        let campusCy = lerp(520.0 * sy, targetCampusY, pRise)
        let campusRect = CGRect(
            x: apexX - campusW * 0.5,
            y: campusCy - campusH * 0.5,
            width: campusW,
            height: campusH
        )
        drawImageTopDown(ctx, res.campus, in: campusRect)

        // Bottom dark scrim for crystal-clear motto readability
        let scrimColors = [
            hexColor(scrimHex, 0.0),
            hexColor(scrimHex, 0.58),
            hexColor(scrimHex, 0.90)
        ] as CFArray
        let scrimGrad = CGGradient(colorsSpace: srgb, colors: scrimColors, locations: [0.0, 0.54, 1.0])!
        ctx.drawLinearGradient(
            scrimGrad,
            start: CGPoint(x: 0, y: triBottomY - CGFloat(315.0 * sy)),
            end: CGPoint(x: 0, y: triBottomY),
            options: [.drawsAfterEndLocation]
        )

        // Radial dark pool behind motto (startRadius: 0 so center never creates a bright hole)
        let poolCx = (mottoXBase + 95.0) * sx
        let poolCy = 625.0 * sy
        let poolColors = [
            hexColor(scrimHex, 0.62),
            hexColor(scrimHex, 0.0)
        ] as CFArray
        let poolGrad = CGGradient(colorsSpace: srgb, colors: poolColors, locations: [0.0, 1.0])!
        ctx.drawRadialGradient(
            poolGrad,
            startCenter: CGPoint(x: poolCx, y: poolCy),
            startRadius: 0,
            endCenter: CGPoint(x: poolCx, y: poolCy),
            endRadius: 245.0 * u,
            options: [.drawsBeforeStartLocation]
        )
        ctx.restoreGState()

        ctx.saveGState()
        ctx.setShadow(offset: .zero, blur: 12.0 * u, color: rgbaColor(235, 215, 165, 0.22))
        drawDynamicTrianglePath(ctx, apexX: CGFloat(apexX), apexY: triApexY, bottomY: triBottomY, slope: triSlope)
        ctx.setStrokeColor(rgbaColor(235, 215, 165, 0.16))
        ctx.setLineWidth(12.0 * u)
        ctx.setLineJoin(.miter)
        ctx.strokePath()
        ctx.restoreGState()

        ctx.saveGState()
        drawDynamicTrianglePath(ctx, apexX: CGFloat(apexX), apexY: triApexY, bottomY: triBottomY, slope: triSlope)
        ctx.setLineWidth(5.5 * u)
        ctx.setLineJoin(.miter)
        ctx.replacePathWithStrokedPath()
        ctx.clip()

        let goldColors = [
            rgbaColor(246, 235, 201, 1.0),
            rgbaColor(198, 174, 122, 1.0),
            rgbaColor(242, 228, 188, 1.0),
            rgbaColor(154, 130, 83, 1.0)
        ] as CFArray
        let goldGrad = CGGradient(colorsSpace: srgb, colors: goldColors, locations: [0.0, 0.35, 0.68, 1.0])!
        ctx.drawLinearGradient(
            goldGrad,
            start: CGPoint(x: 105.0 * sx, y: 745.0 * sy),
            end: CGPoint(x: 1227.0 * sx, y: 152.0 * sy),
            options: [.drawsBeforeStartLocation, .drawsAfterEndLocation]
        )

        if activeGleam >= 0 {
            let gp = easeInOutCubic(activeGleam)
            let centerY = lerp(Double(triBottomY), Double(triApexY) - 10.0 * sy, gp)
            let gleamColors = [
                rgbaColor(255, 249, 228, 0.0),
                rgbaColor(255, 250, 232, 0.92),
                rgbaColor(255, 249, 228, 0.0)
            ] as CFArray
            let gleamGrad = CGGradient(colorsSpace: srgb, colors: gleamColors, locations: [0.0, 0.5, 1.0])!
            ctx.drawLinearGradient(
                gleamGrad,
                start: CGPoint(x: apexX, y: centerY + 110.0 * sy),
                end: CGPoint(x: apexX, y: centerY - 110.0 * sy),
                options: []
            )
        }
        ctx.restoreGState()

        if (triBottomY - triApexY) > CGFloat(40.0 * sy) {
            ctx.saveGState()
            drawDynamicInnerTrianglePath(ctx, apexX: CGFloat(apexX), apexY: triApexY, bottomY: triBottomY, slope: triSlope, scale: CGFloat(u))
            ctx.setStrokeColor(rgbaColor(255, 250, 235, 0.35))
            ctx.setLineWidth(1.0 * u)
            ctx.strokePath()
            ctx.restoreGState()
        }

        if useGroupLayer {
            ctx.endTransparencyLayer()
            ctx.restoreGState()
        }
    }

    // -------------------------------------------------------------------------
    // Layer 3: Circular School Emblem
    // -------------------------------------------------------------------------
    if emblemAlpha > 0.005 {
        let ex: CGFloat = CGFloat(apexX)
        let ey: CGFloat = CGFloat(emblemCenterY)
        let useEmblemLayer = emblemAlpha < 0.999

        if useEmblemLayer {
            ctx.saveGState()
            ctx.setAlpha(CGFloat(emblemAlpha))
            ctx.beginTransparencyLayer(auxiliaryInfo: nil)
        }

        ctx.saveGState()
        ctx.setShadow(offset: CGSize(width: 0, height: -5.0 * u), blur: 26.0 * u, color: hexColor(scrimHex, 0.60))
        ctx.setFillColor(rgbaColor(255, 255, 255, 1.0))
        ctx.fillEllipse(in: CGRect(x: ex - emblemR, y: ey - emblemR, width: emblemR * 2, height: emblemR * 2))
        ctx.restoreGState()

        if ringSweep > 0.005 {
            ctx.saveGState()
            if ringSweep < 0.999 {
                let startAng = -CGFloat.pi / 2.0
                let endAng = startAng + CGFloat.pi * 2.0 * CGFloat(ringSweep)
                ctx.beginPath()
                ctx.move(to: CGPoint(x: ex, y: ey))
                ctx.addArc(center: CGPoint(x: ex, y: ey), radius: outerR + 2.0, startAngle: startAng, endAngle: endAng, clockwise: false)
                ctx.closePath()
                ctx.clip()
            }

            let bezelPath = CGMutablePath()
            bezelPath.addEllipse(in: CGRect(x: ex - outerR, y: ey - outerR, width: outerR * 2, height: outerR * 2))
            bezelPath.addEllipse(in: CGRect(x: ex - bezelInnerR, y: ey - bezelInnerR, width: bezelInnerR * 2, height: bezelInnerR * 2))
            ctx.addPath(bezelPath)
            ctx.clip(using: .evenOdd)

            let bezelColors = [
                rgbaColor(245, 233, 200, 1.0),
                rgbaColor(203, 180, 130, 1.0),
                rgbaColor(248, 238, 210, 1.0),
                rgbaColor(174, 150, 98, 1.0)
            ] as CFArray
            let bezelGrad = CGGradient(colorsSpace: srgb, colors: bezelColors, locations: [0.0, 0.35, 0.65, 1.0])!
            ctx.drawLinearGradient(
                bezelGrad,
                start: CGPoint(x: ex - outerR, y: ey - outerR),
                end: CGPoint(x: ex + outerR, y: ey + outerR),
                options: []
            )

            if activeGleam >= 0 {
                let sp = easeInOutCubic(activeGleam)
                let sxGleam = lerp(Double(ex - outerR - 40), Double(ex + outerR + 40), sp)
                let sheenColors = [
                    rgbaColor(255, 252, 240, 0.0),
                    rgbaColor(255, 252, 240, 0.88),
                    rgbaColor(255, 252, 240, 0.0)
                ] as CFArray
                let sheenGrad = CGGradient(colorsSpace: srgb, colors: sheenColors, locations: [0.0, 0.5, 1.0])!
                ctx.drawLinearGradient(
                    sheenGrad,
                    start: CGPoint(x: sxGleam - 36.0 * u, y: Double(ey) - 36.0 * u),
                    end: CGPoint(x: sxGleam + 36.0 * u, y: Double(ey) + 36.0 * u),
                    options: []
                )
            }
            ctx.restoreGState()
        }

        // Exact emblem accent inner ring
        ctx.saveGState()
        ctx.setFillColor(hexColor(pal.emblem_accent, 1.0))
        ctx.fillEllipse(in: CGRect(x: ex - bezelInnerR, y: ey - bezelInnerR, width: bezelInnerR * 2, height: bezelInnerR * 2))
        ctx.restoreGState()

        ctx.saveGState()
        ctx.addEllipse(in: CGRect(x: ex - emblemR, y: ey - emblemR, width: emblemR * 2, height: emblemR * 2))
        ctx.clip()
        ctx.setFillColor(rgbaColor(255, 255, 255, 1.0))
        ctx.fillEllipse(in: CGRect(x: ex - emblemR, y: ey - emblemR, width: emblemR * 2, height: emblemR * 2))
        drawImageTopDown(ctx, res.emblem, in: CGRect(x: ex - emblemR, y: ey - emblemR, width: emblemR * 2, height: emblemR * 2))
        ctx.restoreGState()

        if useEmblemLayer {
            ctx.endTransparencyLayer()
            ctx.restoreGState()
        }
    }

    // -------------------------------------------------------------------------
    // Layer 4: Top-Left University Title
    // -------------------------------------------------------------------------
    if titleAlpha > 0.005 {
        ctx.saveGState()
        ctx.setAlpha(CGFloat(titleAlpha))
        ctx.translateBy(x: CGFloat(titleDx), y: 0)
        drawTextTopDown(
            ctx,
            res.config.university.name,
            font: res.fontTitleCN,
            color: rgbaColor(246, 249, 255, 1.0),
            x: CGFloat(56.0 * sx),
            topY: CGFloat(52.0 * sy),
            tracking: CGFloat(3.0 * u),
            align: .left,
            shadowColor: hexColor(scrimHex, 0.52),
            shadowBlur: CGFloat(10.0 * u),
            shadowOffsetY: CGFloat(3.0 * u)
        )
        drawTextTopDown(
            ctx,
            res.config.university.english_name,
            font: res.fontTitleEN,
            color: hexColor(subHex, 1.0),
            x: CGFloat(58.0 * sx),
            topY: CGFloat(108.0 * sy),
            tracking: CGFloat(0.8 * u),
            align: .left,
            shadowColor: hexColor(scrimHex, 0.48),
            shadowBlur: CGFloat(6.0 * u),
            shadowOffsetY: CGFloat(2.0 * u)
        )
        ctx.restoreGState()
    }

    // -------------------------------------------------------------------------
    // Layer 5: Bottom-Left Portrait & Fading Nameplate
    // -------------------------------------------------------------------------
    if portraitAlpha > 0.005 {
        ctx.saveGState()
        ctx.setAlpha(CGFloat(portraitAlpha))
        ctx.translateBy(x: CGFloat(portraitDx), y: CGFloat(portraitDy))

        let pHeight = (res.config.layout?.portrait_height ?? 450.0) * sy
        let pAspect = Double(res.portrait.width) / Double(res.portrait.height)
        let pWidth = pHeight * pAspect
        let pCenterX = (res.config.layout?.portrait_x ?? 236.0) * sx
        let pRect = CGRect(x: pCenterX - pWidth * 0.5, y: Double(H) - pHeight, width: pWidth, height: pHeight)

        ctx.saveGState()
        ctx.setShadow(offset: CGSize(width: 4.0 * u, height: -2.0 * u), blur: 20.0 * u, color: hexColor(scrimHex, 0.48))
        drawImageTopDown(ctx, res.portrait, in: pRect)
        ctx.restoreGState()

        ctx.saveGState()
        let ribRect = CGRect(x: 46.0 * sx, y: 576.0 * sy, width: 444.0 * sx, height: 106.0 * sy)
        ctx.clip(to: ribRect)
        let ribColors = [
            hexColor(ribbonHex, 0.84),
            hexColor(ribbonHex, 0.60),
            hexColor(ribbonHex, 0.0)
        ] as CFArray
        let ribGrad = CGGradient(colorsSpace: srgb, colors: ribColors, locations: [0.0, 0.58, 1.0])!
        ctx.drawLinearGradient(
            ribGrad,
            start: CGPoint(x: 46.0 * sx, y: 629.0 * sy),
            end: CGPoint(x: 490.0 * sx, y: 629.0 * sy),
            options: []
        )
        ctx.restoreGState()

        let barH = 84.0 * sy * barReveal
        if barH > 0.5 {
            ctx.saveGState()
            let barColors = [
                rgbaColor(245, 233, 200, 1.0),
                rgbaColor(203, 180, 130, 1.0),
                rgbaColor(156, 133, 86, 1.0)
            ] as CFArray
            let barGrad = CGGradient(colorsSpace: srgb, colors: barColors, locations: [0.0, 0.5, 1.0])!
            ctx.clip(to: CGRect(x: 56.0 * sx, y: 586.0 * sy, width: 3.2 * u, height: barH))
            ctx.drawLinearGradient(barGrad, start: CGPoint(x: 56.0 * sx, y: 586.0 * sy), end: CGPoint(x: 56.0 * sx, y: 670.0 * sy), options: [])
            ctx.restoreGState()
        }

        drawTextTopDown(
            ctx,
            res.config.person.name,
            font: res.fontName,
            color: rgbaColor(255, 255, 255, 1.0),
            x: CGFloat(72.0 * sx),
            topY: CGFloat(585.0 * sy),
            tracking: CGFloat(1.5 * u),
            align: .left,
            shadowColor: rgbaColor(0, 0, 0, 0.55),
            shadowBlur: CGFloat(8.0 * u),
            shadowOffsetY: CGFloat(2.0 * u)
        )

        ctx.saveGState()
        ctx.clip(to: CGRect(x: 72.0 * sx, y: 635.0 * sy, width: 250.0 * sx * barReveal, height: 1.2 * sy))
        let divColors = [
            rgbaColor(232, 217, 181, 0.48),
            rgbaColor(232, 217, 181, 0.0)
        ] as CFArray
        let divGrad = CGGradient(colorsSpace: srgb, colors: divColors, locations: [0.0, 1.0])!
        ctx.drawLinearGradient(divGrad, start: CGPoint(x: 72.0 * sx, y: 635.0 * sy), end: CGPoint(x: 322.0 * sx, y: 635.0 * sy), options: [])
        ctx.restoreGState()

        drawTextTopDown(
            ctx,
            res.config.person.title,
            font: res.fontRole,
            color: hexColor(subHex, 1.0),
            x: CGFloat(72.0 * sx),
            topY: CGFloat(646.0 * sy),
            tracking: CGFloat(0.6 * u),
            align: .left,
            shadowColor: rgbaColor(0, 0, 0, 0.45),
            shadowBlur: CGFloat(6.0 * u),
            shadowOffsetY: CGFloat(2.0 * u)
        )

        ctx.restoreGState()
    }

    // -------------------------------------------------------------------------
    // Layer 6: Right-Side 3D Specialty Icons (Diagonal Cascade)
    // -------------------------------------------------------------------------
    let slots3: [(Double, Double, Double, Double, Double)] = [
        (924.0,  114.0, 0.64, 0.96, 0.0),
        (1066.0, 234.0, 0.74, 1.06, 2.1),
        (1198.0, 366.0, 0.84, 1.16, 4.2)
    ]
    let slots2: [(Double, Double, Double, Double, Double)] = [
        (955.0,  150.0, 0.64, 0.96, 0.0),
        (1140.0, 310.0, 0.78, 1.10, 2.4)
    ]
    let activeSlots = res.disciplines.count == 2 ? slots2 : slots3

    for (idx, disc) in res.disciplines.enumerated() {
        let (baseCx, baseCy, inStart, inEnd, phase) = activeSlots[idx]
        if t < inStart { continue }

        let alpha: Double
        let scale: Double
        let dyAnim: Double
        if t < inEnd {
            let pRaw = progress(t, inStart, inEnd)
            alpha = easeOutCubic(pRaw)
            scale = lerp(0.72, 1.0, easeOutBack(pRaw, overshoot: 1.15))
            dyAnim = lerp(18.0 * sy, 0.0, easeOutQuart(pRaw))
        } else {
            alpha = 1.0; scale = 1.0; dyAnim = 0.0
        }
        if alpha <= 0.005 { continue }

        let floatBlend = easeOutCubic(progress(t, inEnd, inEnd + 0.40))
        let floatY = sin((t - inStart) * 1.9 + phase) * 2.5 * sy * floatBlend
        let cx = baseCx * sx
        let cy = baseCy * sy + dyAnim + floatY

        ctx.saveGState()
        ctx.setAlpha(CGFloat(alpha))

        let shCenterY = cy + 48.0 * u * scale
        let shRx = 40.0 * u * scale
        let shRy = 10.0 * u * scale
        ctx.saveGState()
        ctx.translateBy(x: CGFloat(cx), y: CGFloat(shCenterY))
        ctx.scaleBy(x: CGFloat(shRx), y: CGFloat(shRy))
        let shColors = [
            hexColor(scrimHex, 0.44),
            hexColor(scrimHex, 0.0)
        ] as CFArray
        let shGrad = CGGradient(colorsSpace: srgb, colors: shColors, locations: [0.0, 1.0])!
        ctx.drawRadialGradient(shGrad, startCenter: .zero, startRadius: 0.0, endCenter: .zero, endRadius: 1.0, options: [])
        ctx.restoreGState()

        let iconSz = 114.0 * u * scale
        let iconRect = CGRect(x: cx - iconSz * 0.5, y: cy - iconSz * 0.5, width: iconSz, height: iconSz)
        ctx.saveGState()
        ctx.setShadow(offset: CGSize(width: 0, height: -4.0 * u), blur: 14.0 * u, color: hexColor(scrimHex, 0.36))
        drawImageTopDown(ctx, disc.img, in: iconRect)
        ctx.restoreGState()

        let labelTopY = (baseCy * sy + 60.0 * sy) + dyAnim + floatY * 0.35
        drawTextTopDown(
            ctx,
            disc.name,
            font: res.fontLabel,
            color: rgbaColor(240, 246, 255, 1.0),
            x: CGFloat(cx),
            topY: CGFloat(labelTopY),
            tracking: CGFloat(1.2 * u),
            align: .center,
            shadowColor: rgbaColor(0, 0, 0, 0.62),
            shadowBlur: CGFloat(8.0 * u),
            shadowOffsetY: CGFloat(2.0 * u)
        )

        ctx.restoreGState()
    }

    // -------------------------------------------------------------------------
    // Layer 7: Bottom-Right School Motto
    // -------------------------------------------------------------------------
    if mottoAlpha > 0.005 {
        ctx.saveGState()
        ctx.setAlpha(CGFloat(mottoAlpha))
        ctx.translateBy(x: 0, y: CGFloat(mottoDy))

        let lines = res.config.motto.lines
        let tagText = res.config.motto.label ?? "校 训"
        let tagTopY = (lines.count == 1 ? 592.0 : 558.0) * sy

        drawTextTopDown(
            ctx,
            tagText,
            font: res.fontMottoTag,
            color: rgbaColor(222, 203, 160, 1.0),
            x: CGFloat((mottoXBase + 2.0) * sx),
            topY: CGFloat(tagTopY),
            tracking: CGFloat(4.0 * u),
            align: .left,
            shadowColor: rgbaColor(0, 0, 0, 0.70),
            shadowBlur: CGFloat(6.0 * u),
            shadowOffsetY: CGFloat(2.0 * u)
        )

        for (i, lineText) in lines.prefix(2).enumerated() {
            let lineY = (lines.count == 1 ? 622.0 : (585.0 + Double(i) * 48.0)) * sy
            drawTextTopDown(
                ctx,
                lineText,
                font: res.fontMottoMain,
                color: rgbaColor(248, 250, 255, 1.0),
                x: CGFloat(mottoXBase * sx),
                topY: CGFloat(lineY),
                tracking: CGFloat(5.5 * u),
                align: .left,
                shadowColor: rgbaColor(0, 0, 0, 0.75),
                shadowBlur: CGFloat(10.0 * u),
                shadowOffsetY: CGFloat(3.0 * u)
            )
        }

        ctx.restoreGState()
    }

    ctx.restoreGState()
}

// MARK: - Main Encoding Loop

func main() {
    let cfgPath = parseConfigArg()
    let cfgURL = URL(fileURLWithPath: cfgPath).standardized
    let baseDir = cfgURL.deletingLastPathComponent()

    let data: Data
    do {
        data = try Data(contentsOf: cfgURL)
    } catch {
        fatalError("Failed to read config \(cfgPath): \(error)")
    }

    let config: VideoConfig
    do {
        config = try JSONDecoder().decode(VideoConfig.self, from: data)
    } catch {
        fatalError("Failed to parse config JSON \(cfgPath): \(error)")
    }

    let res = loadResources(config: config, baseDir: baseDir)
    let W = res.W
    let H = res.H
    let FPS = res.FPS
    let DURATION = res.DURATION
    let TOTAL_FRAMES = Int(round(DURATION * Double(FPS)))

    let outputPath = resolvePath(baseDir, config.video?.output ?? "output.mp4")
    let outURL = URL(fileURLWithPath: outputPath)
    try? FileManager.default.createDirectory(at: outURL.deletingLastPathComponent(), withIntermediateDirectories: true)
    if FileManager.default.fileExists(atPath: outputPath) {
        try? FileManager.default.removeItem(at: outURL)
    }

    let previewsDir = resolvePath(baseDir, config.previews_dir ?? "previews")
    try? FileManager.default.createDirectory(at: URL(fileURLWithPath: previewsDir), withIntermediateDirectories: true)

    let writer: AVAssetWriter
    do {
        writer = try AVAssetWriter(outputURL: outURL, fileType: .mp4)
    } catch {
        fatalError("Failed to create AVAssetWriter: \(error)")
    }

    let videoSettings: [String: Any] = [
        AVVideoCodecKey: AVVideoCodecType.h264,
        AVVideoWidthKey: W,
        AVVideoHeightKey: H,
        AVVideoColorPropertiesKey: [
            AVVideoColorPrimariesKey: AVVideoColorPrimaries_ITU_R_709_2,
            AVVideoTransferFunctionKey: AVVideoTransferFunction_ITU_R_709_2,
            AVVideoYCbCrMatrixKey: AVVideoYCbCrMatrix_ITU_R_709_2
        ],
        AVVideoCompressionPropertiesKey: [
            AVVideoAverageBitRateKey: 10_000_000,
            AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
            AVVideoMaxKeyFrameIntervalKey: Int(FPS)
        ]
    ]

    let input = AVAssetWriterInput(mediaType: .video, outputSettings: videoSettings)
    input.expectsMediaDataInRealTime = false

    let pbAttrs: [String: Any] = [
        kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
        kCVPixelBufferWidthKey as String: W,
        kCVPixelBufferHeightKey as String: H,
        kCVPixelBufferCGImageCompatibilityKey as String: true,
        kCVPixelBufferCGBitmapContextCompatibilityKey as String: true
    ]
    let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: pbAttrs)

    guard writer.canAdd(input) else {
        fatalError("Cannot add AVAssetWriterInput")
    }
    writer.add(input)

    guard writer.startWriting() else {
        fatalError("AVAssetWriter failed to start: \(String(describing: writer.error))")
    }
    writer.startSession(atSourceTime: .zero)

    let previewTargets: [(Int, String)] = [
        (Int(round(0.20 * Double(FPS))), "preview_t020.png"),
        (Int(round(0.45 * Double(FPS))), "preview_t045.png"),
        (Int(round(0.65 * Double(FPS))), "preview_t065.png"),
        (Int(round(0.85 * Double(FPS))), "preview_t085.png"),
        (Int(round(1.30 * Double(FPS))), "preview_t130.png"),
        (min(TOTAL_FRAMES - 1, Int(round(3.00 * Double(FPS)))), "preview_t300.png")
    ]

    for frameIdx in 0..<TOTAL_FRAMES {
        while !input.isReadyForMoreMediaData {
            usleep(2000)
        }

        var pxOpt: CVPixelBuffer?
        let poolStatus = CVPixelBufferPoolCreatePixelBuffer(nil, adaptor.pixelBufferPool!, &pxOpt)
        guard poolStatus == kCVReturnSuccess, let pixelBuffer = pxOpt else {
            fatalError("Failed to allocate pixel buffer at frame \(frameIdx): \(poolStatus)")
        }

        CVPixelBufferLockBaseAddress(pixelBuffer, [])
        let baseAddr = CVPixelBufferGetBaseAddress(pixelBuffer)!
        let bytesPerRow = CVPixelBufferGetBytesPerRow(pixelBuffer)

        let bitmapInfo = CGBitmapInfo.byteOrder32Little.rawValue | CGImageAlphaInfo.premultipliedFirst.rawValue
        guard let ctx = CGContext(
            data: baseAddr,
            width: W,
            height: H,
            bitsPerComponent: 8,
            bytesPerRow: bytesPerRow,
            space: srgb,
            bitmapInfo: bitmapInfo
        ) else {
            fatalError("Failed to create CGContext")
        }

        let t = Double(frameIdx) / Double(FPS)
        renderFrame(into: ctx, res: res, t: t)

        for (targetIdx, fname) in previewTargets where frameIdx == targetIdx {
            if let snap = ctx.makeImage() {
                savePNG(snap, to: "\(previewsDir)/\(fname)")
                print("Saved preview: \(previewsDir)/\(fname) at t=\(String(format: "%.2f", t))s")
            }
        }

        CVPixelBufferUnlockBaseAddress(pixelBuffer, [])

        let pts = CMTime(value: CMTimeValue(frameIdx), timescale: CMTimeScale(FPS))
        if !adaptor.append(pixelBuffer, withPresentationTime: pts) {
            fatalError("Failed to append pixel buffer at frame \(frameIdx): \(String(describing: writer.error))")
        }
    }

    input.markAsFinished()
    let sem = DispatchSemaphore(value: 0)
    writer.finishWriting {
        sem.signal()
    }
    sem.wait()

    if writer.status != .completed {
        fatalError("AVAssetWriter finished with status \(writer.status.rawValue): \(String(describing: writer.error))")
    }
    print("Successfully rendered \(outputPath) (\(TOTAL_FRAMES) frames @ \(FPS)fps, \(DURATION)s, 0 audio tracks)")
}

main()
