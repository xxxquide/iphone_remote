// swift-tools-version:5.9
import PackageDescription

// Tiny macOS CLI: OCR an image with Apple's Vision framework, print JSON words
// with pixel bounding boxes. Used by the Python targeting cascade (vision/ocr.py).
//
// Build:  cd tools/visionocr && swift build -c release
// Install: cp .build/release/visionocr /usr/local/bin/   (or add to PATH)
let package = Package(
    name: "visionocr",
    platforms: [.macOS(.v13)],
    targets: [ .executableTarget(name: "visionocr", path: "Sources/visionocr") ]
)
