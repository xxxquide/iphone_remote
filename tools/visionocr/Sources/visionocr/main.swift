import Foundation
import Vision
import AppKit

// Usage: visionocr <image-path>
// Prints: JSON array [{ "text","x","y","w","h","conf" }] in image PIXEL coords
// (top-left origin). Exit non-zero on error.

func fail(_ msg: String) -> Never {
    FileHandle.standardError.write((msg + "\n").data(using: .utf8)!)
    exit(1)
}

guard CommandLine.arguments.count >= 2 else { fail("usage: visionocr <image-path>") }
let path = CommandLine.arguments[1]

guard let image = NSImage(contentsOfFile: path),
      let tiff = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff),
      let cg = bitmap.cgImage else { fail("cannot load image: \(path)") }

let W = CGFloat(cg.width)
let H = CGFloat(cg.height)

struct Word: Codable { let text: String; let x, y, w, h, conf: Double }
var words: [Word] = []

let request = VNRecognizeTextRequest { req, err in
    if let err = err { fail("vision error: \(err.localizedDescription)") }
    for obs in (req.results as? [VNRecognizedTextObservation]) ?? [] {
        guard let cand = obs.topCandidates(1).first else { continue }
        // Vision boundingBox: normalized, origin bottom-left -> convert to top-left pixels.
        let bb = obs.boundingBox
        let x = Double(bb.minX * W)
        let y = Double((1 - bb.maxY) * H)
        let w = Double(bb.width * W)
        let h = Double(bb.height * H)
        words.append(Word(text: cand.string, x: x, y: y, w: w, h: h,
                          conf: Double(cand.confidence)))
    }
}
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: cg, options: [:])
do { try handler.perform([request]) } catch { fail("perform failed: \(error)") }

let data = try JSONEncoder().encode(words)
FileHandle.standardOutput.write(data)
