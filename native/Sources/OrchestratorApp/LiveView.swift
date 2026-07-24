import SwiftUI
import AppKit
import AVFoundation
import CoreMediaIO

// Native live-view (UI variation A).
//   Primary : AVFoundation USB capture of the iPhone (lowest latency).
//   Fallback: MJPEG stream from the core (/api/devices/{udid}/stream).
// Clicks map to real device points using the logical screen size the core
// exposes (point_w/point_h), so taps land where you click regardless of
// letterboxing.
//
// One-time macOS setup: the app needs Camera permission (capturing an iPhone
// counts as camera access) -> add NSCameraUsageDescription to Info.plist and
// approve the prompt. See native/README.md.

// MARK: - Enable iOS devices as capture sources (CoreMediaIO "DAL")
func enableDALDevices() {
    var address = CMIOObjectPropertyAddress(
        mSelector: CMIOObjectPropertySelector(kCMIOHardwarePropertyAllowScreenCaptureDevices),
        mScope: CMIOObjectPropertyScope(kCMIOObjectPropertyScopeGlobal),
        mElement: CMIOObjectPropertyElement(kCMIOObjectPropertyElementMain))
    var allow: UInt32 = 1
    CMIOObjectSetPropertyData(CMIOObjectID(kCMIOObjectSystemObject), &address, 0, nil,
                              UInt32(MemoryLayout<UInt32>.size), &allow)
}

// MARK: - MJPEG fallback reader (parses concatenated JPEG frames)
final class MJPEGReader: NSObject, URLSessionDataDelegate {
    var onImage: ((CGImage) -> Void)?
    private var buffer = Data()
    private var session: URLSession?
    private var task: URLSessionDataTask?
    private let soi = Data([0xFF, 0xD8])       // JPEG start-of-image
    private let eoi = Data([0xFF, 0xD9])       // JPEG end-of-image

    func start(url: URL, token: String) {
        var req = URLRequest(url: url)
        req.timeoutInterval = 3600
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        let s = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
        session = s
        task = s.dataTask(with: req)
        task?.resume()
    }

    func stop() {
        task?.cancel()
        session?.invalidateAndCancel()
        buffer.removeAll()
    }

    func urlSession(_ s: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        buffer.append(data)
        while let start = buffer.range(of: soi),
              let end = buffer.range(of: eoi, in: start.upperBound..<buffer.endIndex) {
            let frame = buffer.subdata(in: start.lowerBound..<end.upperBound)
            buffer.removeSubrange(buffer.startIndex..<end.upperBound)
            if let img = NSImage(data: frame),
               let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) {
                onImage?(cg)
            }
        }
        if buffer.count > 8_000_000 { buffer.removeAll() }   // safety cap
    }
}

// MARK: - Controller: pick capture or MJPEG, drive the view
@MainActor
final class LiveController: ObservableObject {
    enum Mode { case idle, capture, mjpeg }
    @Published var status = "starting…"

    let session = AVCaptureSession()
    private let mjpeg = MJPEGReader()
    private weak var view: LiveNSView?
    private var latest: CGImage?
    private var mode: Mode = .idle

    func attach(_ v: LiveNSView) { view = v; render() }

    func start(udid: String, baseURL: URL, token: String) {
        enableDALDevices()
        AVCaptureDevice.requestAccess(for: .video) { _ in }
        if let device = Self.findDevice(udid: udid) {
            setupCapture(device)
        } else {
            setupMJPEG(udid: udid, baseURL: baseURL, token: token)
        }
    }

    func stop() {
        if session.isRunning { session.stopRunning() }
        session.inputs.forEach { session.removeInput($0) }
        mjpeg.stop()
        mode = .idle
    }

    private func setupCapture(_ device: AVCaptureDevice) {
        session.beginConfiguration()
        session.inputs.forEach { session.removeInput($0) }
        if let input = try? AVCaptureDeviceInput(device: device), session.canAddInput(input) {
            session.addInput(input)
        }
        session.commitConfiguration()
        if !session.isRunning { session.startRunning() }
        mode = .capture
        status = "AVFoundation · \(device.localizedName)"
        render()
    }

    private func setupMJPEG(udid: String, baseURL: URL, token: String) {
        let url = baseURL.appendingPathComponent("api/devices/\(udid)/stream")
        mjpeg.onImage = { [weak self] cg in
            Task { @MainActor in
                self?.latest = cg
                self?.view?.showImage(cg)
            }
        }
        mjpeg.start(url: url, token: token)
        mode = .mjpeg
        status = "MJPEG fallback · no USB capture device"
        render()
    }

    private func render() {
        guard let v = view else { return }
        switch mode {
        case .capture: v.showCapture(session)
        case .mjpeg:   if let cg = latest { v.showImage(cg) }
        case .idle:    break
        }
    }

    /// The iPhone screen-capture device's uniqueID equals its UDID.
    static func findDevice(udid: String) -> AVCaptureDevice? {
        let ds = AVCaptureDevice.DiscoverySession(
            deviceTypes: [.external], mediaType: nil, position: .unspecified)
        return ds.devices.first { $0.uniqueID == udid } ?? ds.devices.first
    }
}

// MARK: - Layer-backed view that renders capture OR image and maps taps
final class LiveNSView: NSView {
    override var isFlipped: Bool { true }          // origin top-left, like the phone
    let previewLayer = AVCaptureVideoPreviewLayer()
    let imageLayer = CALayer()
    var logicalSize = CGSize(width: 390, height: 844)
    var onTap: ((CGFloat, CGFloat) -> Void)?

    override init(frame: NSRect) {
        super.init(frame: frame)
        wantsLayer = true
        layer?.backgroundColor = NSColor.black.cgColor
        previewLayer.videoGravity = .resizeAspect
        imageLayer.contentsGravity = .resizeAspect
        imageLayer.backgroundColor = NSColor.black.cgColor
        imageLayer.isHidden = true
        layer?.addSublayer(imageLayer)
        layer?.addSublayer(previewLayer)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) not used") }

    override func layout() {
        super.layout()
        previewLayer.frame = bounds
        imageLayer.frame = bounds
    }

    func showCapture(_ session: AVCaptureSession) {
        previewLayer.session = session
        previewLayer.isHidden = false
        imageLayer.isHidden = true
    }

    func showImage(_ cg: CGImage) {
        CATransaction.begin()
        CATransaction.setDisableActions(true)      // no implicit fade between frames
        imageLayer.contents = cg
        CATransaction.commit()
        imageLayer.isHidden = false
        previewLayer.isHidden = true
    }

    /// Aspect-fit rect of the phone screen inside the view bounds.
    private func contentRect() -> CGRect {
        let ar = logicalSize.width / max(logicalSize.height, 1)
        let b = bounds
        var w = b.width, h = w / ar
        if h > b.height { h = b.height; w = h * ar }
        return CGRect(x: (b.width - w) / 2, y: (b.height - h) / 2, width: w, height: h)
    }

    override func mouseDown(with event: NSEvent) {
        let p = convert(event.locationInWindow, from: nil)   // flipped: top-left origin
        let r = contentRect()
        guard r.contains(p) else { return }
        let nx = (p.x - r.minX) / r.width
        let ny = (p.y - r.minY) / r.height
        onTap?(nx * logicalSize.width, ny * logicalSize.height)
    }
}

struct LivePreview: NSViewRepresentable {
    @ObservedObject var controller: LiveController
    let logicalSize: CGSize
    let onTap: (CGFloat, CGFloat) -> Void

    func makeNSView(context: Context) -> LiveNSView {
        let v = LiveNSView()
        v.logicalSize = logicalSize
        v.onTap = onTap
        controller.attach(v)
        return v
    }
    func updateNSView(_ nsView: LiveNSView, context: Context) {
        nsView.logicalSize = logicalSize
        nsView.onTap = onTap
    }
}

// MARK: - SwiftUI entry point
struct LiveView: View {
    @EnvironmentObject var core: CoreClient
    let udid: String
    @StateObject private var controller = LiveController()

    private var device: Device? { core.devices.first { $0.udid == udid } }
    private var logicalSize: CGSize {
        CGSize(width: device?.pointW ?? 390, height: device?.pointH ?? 844)
    }

    var body: some View {
        VStack(spacing: 6) {
            LivePreview(controller: controller, logicalSize: logicalSize) { x, y in
                Task { await core.tap(udid, x: Double(x), y: Double(y)) }
            }
            .aspectRatio(logicalSize.width / logicalSize.height, contentMode: .fit)
            .background(.black)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            Text(controller.status)
                .font(.caption2).monospaced().foregroundStyle(.secondary)
        }
        .padding(8)
        .task(id: udid) {
            controller.stop()
            controller.start(udid: udid, baseURL: core.baseURL, token: core.apiToken)
        }
        .onDisappear { controller.stop() }
    }
}
