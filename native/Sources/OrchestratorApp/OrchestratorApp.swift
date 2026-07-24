import SwiftUI

// Native client (UI variation A). Menu-bar agent + main window, both driven by
// the same local core API the browser dashboard uses. This is a skeleton:
// wire real live-view (AVFoundation USB capture) and TCC prompts in Phase 1.

@main
struct OrchestratorApp: App {
    @StateObject private var core = CoreClient()

    var body: some Scene {
        WindowGroup("iPhone Orchestrator") {
            ContentView()
                .environmentObject(core)
                .frame(minWidth: 900, minHeight: 600)
                .task { await core.start() }
        }

        // Menu-bar presence. In a real app set LSUIElement=YES for menu-bar-only.
        MenuBarExtra("Orchestrator", systemImage: "iphone.gen3") {
            Button("Открыть панель") { NSApp.activate(ignoringOtherApps: true) }
            Divider()
            ForEach(core.devices) { d in
                Text("\(d.name) · WDA \(d.wda)")
            }
            Divider()
            Button("Выход") { NSApp.terminate(nil) }
        }
    }
}

struct ContentView: View {
    @EnvironmentObject var core: CoreClient
    @State private var selected: String?

    var body: some View {
        NavigationSplitView {
            DeviceListView(selected: $selected)
        } detail: {
            if let udid = selected ?? core.devices.first?.id {
                DeviceDetailView(udid: udid)
            } else {
                ContentUnavailableView("Нет устройств", systemImage: "iphone.slash")
            }
        }
        .navigationTitle("iPhone Orchestrator")
    }
}
