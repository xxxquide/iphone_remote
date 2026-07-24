import Foundation

struct Device: Identifiable, Codable {
    var udid: String
    var name: String
    var ios: String
    var status: String
    var wda: String
    var tunnel: String
    var ip: String?
    var pointW: Double?
    var pointH: Double?
    var id: String { udid }

    enum CodingKeys: String, CodingKey {
        case udid, name, ios, status, wda, tunnel, ip
        case pointW = "point_w"
        case pointH = "point_h"
    }
}

struct RunResponse: Codable { let task_id: String }
struct Health: Codable { let ok: Bool; let mock: Bool; let version: String }
