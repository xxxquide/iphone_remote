import Foundation
import Security

// Reads the API token the core stores in the login Keychain
// (service "com.orchestrator.api", account "token"). Falls back to the shared
// default so the app still works before the core has run once.
//
// NOTE: the core writes this item from Python (`security add-generic-password`);
// the first time the native app reads it, macOS may prompt to allow access —
// approve once ("Always Allow").
enum KeychainToken {
    static let service = "com.orchestrator.api"
    static let account = "token"
    static let fallback = "dev-local-token"

    static func read() -> String {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess,
              let data = item as? Data,
              let token = String(data: data, encoding: .utf8),
              !token.isEmpty else {
            return fallback
        }
        return token
    }
}
