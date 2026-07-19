import 'dart:convert';
import 'package:http/http.dart' as http;

import 'data/api_client.dart' show kApiBase;
import 'data/ops_repository.dart' show kUseMockData;

/// Runtime backend configuration.
///
/// The backend URL is read at startup from `web/config.json`
/// (`{"apiBaseUrl": "https://..."}`) so it can be changed without rebuilding the
/// app. Returns `null` when there is no usable URL — the app then keeps the
/// bundled mock data and still renders fully, so a missing/unreachable config
/// never leaves a blank screen.
class AppConfig {
  static Future<String?> resolveApiBaseUrl() async {
    // 1) Runtime config.json, served next to index.html.
    try {
      final res = await http
          .get(Uri.base.resolve('config.json'))
          .timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final url = (data['apiBaseUrl'] ?? '').toString().trim();
        if (url.isNotEmpty && !url.contains('PLACEHOLDER')) {
          return url.replaceAll(RegExp(r'/+$'), '');
        }
      }
    } catch (_) {
      // missing / unreachable / invalid JSON -> fall through to mock
    }
    // 2) Optional compile-time override (--dart-define=USE_MOCK=false --dart-define=API_BASE=...).
    if (!kUseMockData && kApiBase.isNotEmpty) {
      return kApiBase.replaceAll(RegExp(r'/+$'), '');
    }
    return null; // -> mock mode
  }
}
