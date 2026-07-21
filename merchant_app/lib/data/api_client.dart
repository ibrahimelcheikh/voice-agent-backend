import 'dart:convert';
import 'package:http/http.dart' as http;

/// Base URL of the AtlasPrimeX backend. Override at build/run time with
/// `--dart-define=API_BASE=https://your-backend.up.railway.app`.
const String kApiBase = String.fromEnvironment('API_BASE', defaultValue: 'http://localhost:8030');

/// Thin authenticated JSON client for /api/v1.
class ApiClient {
  ApiClient({String? base}) : base = base ?? kApiBase;
  final String base;
  String? token;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Uri _u(String path, [Map<String, dynamic>? query]) =>
      Uri.parse('$base/api/v1$path').replace(
        queryParameters: query?.map((k, v) => MapEntry(k, '$v')),
      );

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) async {
    final r = await http.get(_u(path, query), headers: _headers);
    return _decode(r);
  }

  Future<dynamic> post(String path, Object body) async {
    final r = await http.post(_u(path), headers: _headers, body: jsonEncode(body));
    return _decode(r);
  }

  Future<dynamic> put(String path, Object body) async {
    final r = await http.put(_u(path), headers: _headers, body: jsonEncode(body));
    return _decode(r);
  }

  Future<dynamic> patch(String path, Object body) async {
    final r = await http.patch(_u(path), headers: _headers, body: jsonEncode(body));
    return _decode(r);
  }

  Future<dynamic> delete(String path) async {
    final r = await http.delete(_u(path), headers: _headers);
    return _decode(r);
  }

  dynamic _decode(http.Response r) {
    if (r.statusCode >= 200 && r.statusCode < 300) {
      return r.body.isEmpty ? null : jsonDecode(r.body);
    }
    throw ApiException(r.statusCode, r.body);
  }

  /// Log in and store the token. Returns the `user` payload.
  Future<Map<String, dynamic>> login(String email, String password) async {
    final res = await post('/auth/login', {'email': email, 'password': password});
    token = res['access_token'] as String;
    return (res['user'] as Map).cast<String, dynamic>();
  }
}

class ApiException implements Exception {
  ApiException(this.status, this.body);
  final int status;
  final String body;
  @override
  String toString() => 'ApiException($status): $body';
}
