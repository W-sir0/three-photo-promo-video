import Foundation
import Vision
import CoreGraphics
import ImageIO
import CoreVideo

let args = CommandLine.arguments
guard args.count >= 3 else {
    fputs("Usage: segment_portrait <src_image_path> <dst_mask_png_path>\n", stderr)
    exit(1)
}

let srcPath = args[1]
let dstPath = args[2]

guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: srcPath) as CFURL, nil),
      let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
    fputs("Error: Failed to load source image at \(srcPath)\n", stderr)
    exit(1)
}

let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8

let handler = VNImageRequestHandler(cgImage: img, options: [:])
do {
    try handler.perform([req])
} catch {
    fputs("Error: Vision segmentation failed: \(error)\n", stderr)
    exit(2)
}

guard let result = req.results?.first else {
    fputs("Error: No person segmentation result returned.\n", stderr)
    exit(1)
}

let pb = result.pixelBuffer
CVPixelBufferLockBaseAddress(pb, .readOnly)
defer { CVPixelBufferUnlockBaseAddress(pb, .readOnly) }

let w = CVPixelBufferGetWidth(pb)
let h = CVPixelBufferGetHeight(pb)
let bpr = CVPixelBufferGetBytesPerRow(pb)
let base = CVPixelBufferGetBaseAddress(pb)!

let grayCS = CGColorSpaceCreateDeviceGray()
guard let ctx = CGContext(
    data: base,
    width: w,
    height: h,
    bitsPerComponent: 8,
    bytesPerRow: bpr,
    space: grayCS,
    bitmapInfo: CGImageAlphaInfo.none.rawValue
), let maskImg = ctx.makeImage() else {
    fputs("Error: Failed to construct CGImage from mask pixel buffer.\n", stderr)
    exit(1)
}

let dstURL = URL(fileURLWithPath: dstPath)
try? FileManager.default.createDirectory(at: dstURL.deletingLastPathComponent(), withIntermediateDirectories: true)

guard let dst = CGImageDestinationCreateWithURL(dstURL as CFURL, "public.png" as CFString, 1, nil) else {
    fputs("Error: Failed to create PNG destination at \(dstPath)\n", stderr)
    exit(1)
}
CGImageDestinationAddImage(dst, maskImg, nil)
guard CGImageDestinationFinalize(dst) else {
    fputs("Error: Failed to finalize mask PNG at \(dstPath)\n", stderr)
    exit(1)
}

print("Saved mask \(dstPath) (\(w)x\(h))")
