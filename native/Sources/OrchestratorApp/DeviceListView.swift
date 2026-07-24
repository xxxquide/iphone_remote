import SwiftUI

struct DeviceListView: View {
    @EnvironmentObject var core: CoreClient
    @Binding var selected: String?

    var body: some View {
        List(core.devices, selection: $selected) { d in
            VStack(alignment: .leading, spacing: 4) {
                Text(d.name).font(.headline)
                HStack(spacing: 10) {
                    Label("iOS \(d.ios)", systemImage: "gear")
                    StatusPill(label: "WDA", value: d.wda, good: d.wda == "ready")
                    StatusPill(label: "tunnel", value: d.tunnel, good: d.tunnel == "up")
                }
                .font(.caption).foregroundStyle(.secondary)
            }
            .padding(.vertical, 4)
            .tag(d.udid)
        }
        .navigationTitle("Устройства")
    }
}

struct StatusPill: View {
    let label: String, value: String, good: Bool
    var body: some View {
        Text("\(label) \(value)")
            .font(.caption2).monospaced()
            .padding(.horizontal, 6).padding(.vertical, 2)
            .background(good ? Color.green.opacity(0.18) : Color.red.opacity(0.18))
            .foregroundStyle(good ? .green : .red)
            .clipShape(Capsule())
    }
}
