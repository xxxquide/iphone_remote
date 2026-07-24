import SwiftUI

struct DeviceDetailView: View {
    @EnvironmentObject var core: CoreClient
    let udid: String
    @State private var caption = ""
    @State private var mediaPath = ""
    @State private var typeText = ""
    @State private var lastTask = ""

    var body: some View {
        HSplitView {
            LiveView(udid: udid).frame(minWidth: 320)

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    GroupBox("Ручное управление") {
                        HStack {
                            TextField("текст для ввода…", text: $typeText)
                            Button("⌨ Type") { Task { await core.type(udid, text: typeText) } }
                        }
                    }
                    GroupBox("Сценарий: TikTok upload") {
                        VStack(alignment: .leading) {
                            TextField("media_path", text: $mediaPath)
                            TextField("caption", text: $caption)
                            Button("▶ Запустить") {
                                Task {
                                    lastTask = await core.run(
                                        scenario: "tiktok_upload", udid: udid,
                                        params: ["media_path": mediaPath, "caption": caption]) ?? "—"
                                }
                            }
                            if !lastTask.isEmpty { Text("task: \(lastTask)").font(.caption).monospaced() }
                        }
                    }
                    GroupBox("Последнее событие") {
                        Text(core.lastEvent).font(.caption).monospaced()
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }.padding()
            }.frame(minWidth: 300)
        }
        .navigationTitle(core.devices.first { $0.udid == udid }?.name ?? "Устройство")
    }
}
