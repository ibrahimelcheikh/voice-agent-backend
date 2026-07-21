import 'dart:convert';
import 'package:http/http.dart' as http;

import 'data/api_client.dart' show kApiBase;
import 'data/merchant_repository.dart' show kUseMockData;

/// Resolved runtime configuration (from web/config.json).
class AppConfigData {
  const AppConfigData({this.apiBaseUrl, this.useRealApi = false, this.tenantSlug});

  /// Backend base URL, or null when there is no usable one (→ mock mode).
  final String? apiBaseUrl;

  /// When true (and apiBaseUrl set), the dashboard fetches REAL data from the
  /// no-auth /api/v1/tenants/{slug}/… endpoints for Overview/Conversations/Appointments.
  final bool useRealApi;

  /// Which tenant to show (e.g. "apx-divinia").
  final String? tenantSlug;

  bool get realDashboard => useRealApi && apiBaseUrl != null && (tenantSlug ?? '').isNotEmpty;
}

/// Runtime backend configuration.
///
/// Read at startup from `web/config.json`:
/// `{"apiBaseUrl": "https://…", "useRealApi": true, "tenantSlug": "apx-divinia"}`.
/// A missing/unreachable/invalid config leaves the app on bundled mock data so it
/// always renders fully.
class AppConfig {
  static Future<AppConfigData> resolve() async {
    try {
      final res = await http
          .get(Uri.base.resolve('config.json'))
          .timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        var url = (data['apiBaseUrl'] ?? '').toString().trim();
        if (url.contains('PLACEHOLDER')) url = '';
        url = url.replaceAll(RegExp(r'/+$'), '');
        final slug = (data['tenantSlug'] ?? '').toString().trim();
        return AppConfigData(
          apiBaseUrl: url.isEmpty ? _compileTimeBase() : url,
          useRealApi: data['useRealApi'] == true,
          tenantSlug: slug.isEmpty ? null : slug,
        );
      }
    } catch (_) {
      // missing / unreachable / invalid JSON -> fall through
    }
    return AppConfigData(apiBaseUrl: _compileTimeBase());
  }

  /// Optional compile-time override (--dart-define=USE_MOCK=false --dart-define=API_BASE=…).
  static String? _compileTimeBase() {
    if (!kUseMockData && kApiBase.isNotEmpty) {
      return kApiBase.replaceAll(RegExp(r'/+$'), '');
    }
    return null;
  }

  /// Back-compat helper (login-gate path): just the base URL, or null.
  static Future<String?> resolveApiBaseUrl() async => (await resolve()).apiBaseUrl;
}
