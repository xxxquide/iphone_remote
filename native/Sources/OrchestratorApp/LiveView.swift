import SwiftUI

// Live-view for the native client.
// Phase 1 options, fastest first:
//   * AVFoundation USB capture of the iPhone (lowest latency, macOS-native) —
//     add an AVCaptureSession reading the device as an external capture device.
//   * MJPEG from the core (/api/devices/{udid}/stream) — reuse the browser path.
// This skeleton renders a placeholder + forwards clicks as taps.
struct LiveView: View {
    @EnvironmentObject var core: CoreClient
    let udid: String
    // Logical point size of the device screen (approx; refine per device).
    private let logical = CGSize(width: 390, height: 844)

    var body: some View {
        GeometryReader { geo in
            ZStack {
                Color.black
                VStack(spacing: 8) {
                    Image(systemName: "iphone.gen3").font(.system(size: 60)).foregroundStyle(.blue)
                    Text("LIVE-VIEW").font(.headline).foregroundStyle(.white)
                    Text("TODO: AVFoundation capture / MJPEG")
                        .font(.caption).foregroundStyle(.secondary)
                    Text(udid).font(.caption2).monospaced().foregroundStyle(.secondary)
                }
            }
            .contentShape(Rectangle())
            .onTapGesture { location in
                let x = location.x / geo.size.width * logical.width
                let y = location.y / geo.size.height * logical.height
                Task { await core.tap(udid, x: x, y: y) }
            }
        }
        .aspectRatio(logical.width / logical.height, contentMode: .fit)
        .background(.black)
    }
}
