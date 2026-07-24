import Foundation
import Combine

// REST + WebSocket client to the local core service (127.0.0.1:8787).
@MainActor
final class CoreClient: ObservableObject {
    @Published var devices: [Device] = []
    @Published var connected = false
    @Published var lastEvent: String = ""

    let baseURL = URL(string: "http://127.0.0.1:8787")!
    let apiToken = KeychainToken.read()            // shared with the core via Keychain
    private var ws: URLSessionWebSocketTask?

    func start() async {
        await refreshDevices()
        connectWS()
    }

    private func authed(_ path: String, method: String = "GET", body: Data? = nil) -> URLRequest {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = method
        req.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        return req
    }

    func refreshDevices() async {
        do {
            let (data, _) = try await URLSession.shared.data(for: authed("/api/devices"))
            devices = try JSONDecoder().decode([Device].self, from: data)
        } catch { lastEvent = "devices error: \(error.localizedDescription)" }
    }

    func tap(_ udid: String, x: Double, y: Double) async {
        let body = try? JSONSerialization.data(withJSONObject: ["x": x, "y": y])
        _ = try? await URLSession.shared.data(for: authed("/api/devices/\(udid)/tap", method: "POST", body: body))
    }

    func type(_ udid: String, text: String) async {
        let body = try? JSONSerialization.data(withJSONObject: ["text": text])
        _ = try? await URLSession.shared.data(for: authed("/api/devices/\(udid)/type", method: "POST", body: body))
    }

    func run(scenario: String, udid: String, params: [String: String]) async -> String? {
        let body = try? JSONSerialization.data(withJSONObject: ["udid": udid, "params": params])
        guard let (data, _) = try? await URLSession.shared.data(
            for: authed("/api/scenarios/\(scenario)/run", method: "POST", body: body)) else { return nil }
        return (try? JSONDecoder().decode(RunResponse.self, from: data))?.task_id
    }

    // MARK: WebSocket events
    private func connectWS() {
        let wsURL = URL(string: "ws://\(baseURL.host ?? "127.0.0.1"):\(baseURL.port ?? 8787)/ws")!
        var req = URLRequest(url: wsURL)
        req.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        ws = URLSession.shared.webSocketTask(with: req)
        ws?.resume()
        connected = true
        receive()
    }

    private func receive() {
        ws?.receive { [weak self] result in
            guard let self else { return }
            if case .success(.string(let text)) = result {
                Task { @MainActor in self.lastEvent = text }
            }
            self.receive()
        }
    }
}
