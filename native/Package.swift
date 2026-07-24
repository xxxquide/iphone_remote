// swift-tools-version:5.9
import PackageDescription

// Skeleton executable for the native client (UI variation A).
// For the real menu-bar app with TCC entitlements, create a macOS App target in
// Xcode and add Sources/OrchestratorApp/*.swift (see native/README.md).
let package = Package(
    name: "OrchestratorApp",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(
            name: "OrchestratorApp",
            path: "Sources/OrchestratorApp"
        )
    ]
)
