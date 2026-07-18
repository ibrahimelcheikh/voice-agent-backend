import 'api_client.dart';
import 'mock_data.dart';
import 'models.dart';
import 'ops_repository.dart';

/// Live implementation of [OpsRepository]. Operators see the whole fleet. Hydrates
/// /api/v1 into caches once, then serves the existing synchronous screens unchanged.
class ApiOpsRepository implements OpsRepository {
  ApiOpsRepository(this.api);
  final ApiClient api;

  List<Merchant> _merchants = const [];
  List<OpsAlert> _alerts = const [];
  List<Ticket> _tickets = const [];
  List<OpsUser> _users = const [];
  List<int> _fleetVol = const [];

  Future<void> hydrate() async {
    final t = await api.get('/tenants');
    _merchants = [for (final m in (t['items'] as List)) _merchant(m)];

    final a = await api.get('/alerts');
    _alerts = [for (final m in (a['items'] as List)) _alert(m)];

    final tk = await api.get('/tickets');
    _tickets = [for (final m in (tk['items'] as List)) _ticket(m)];

    final u = await api.get('/users');
    _users = [for (final m in (u['items'] as List)) _user(m)];

    try {
      final f = await api.get('/analytics/fleet');
      _fleetVol = [for (final v in ((f['call_volume'] as List?) ?? const [])) (v as num).toInt()];
    } catch (_) {}
    if (_fleetVol.isEmpty) _fleetVol = kFleetVol;
  }

  Merchant _merchant(Map m) => Merchant(
        id: (m['id']).hashCode,
        name: '${m['name']}',
        city: '${m['city'] ?? ''}',
        type: '${m['type'] ?? ''}',
        plan: '${m['plan'] ?? 'Starter'}',
        status: '${m['status'] ?? 'live'}',
        calls: (m['calls'] as num?)?.toInt() ?? 0,
        bookings: (m['bookings'] as num?)?.toInt() ?? 0,
        mrr: (m['mrr'] as num?)?.toInt() ?? 0,
        health: (m['health'] as num?)?.toInt() ?? 0,
        langs: [for (final l in ((m['langs'] as List?) ?? const ['en'])) '$l'],
      );

  OpsAlert _alert(Map m) => OpsAlert(
        id: (m['id']).hashCode,
        sev: '${m['sev'] ?? 'info'}',
        title: '${m['title']}',
        merchant: '${m['merchant'] ?? ''}',
        time: '${m['time'] ?? ''}',
        body: '${m['body'] ?? ''}',
      );

  Ticket _ticket(Map m) => Ticket(
        id: '${m['id']}',
        subject: '${m['subject']}',
        merchant: '${m['merchant'] ?? ''}',
        status: '${m['status'] ?? 'open'}',
        pri: '${m['pri'] ?? 'medium'}',
        agent: '${m['agent'] ?? '—'}',
        time: '${m['time'] ?? ''}',
      );

  OpsUser _user(Map m) => OpsUser(
        id: (m['id']).hashCode,
        name: '${m['name']}',
        email: '${m['email']}',
        role: '${m['role'] ?? 'Support'}',
        active: m['active'] == true,
      );

  @override
  List<Merchant> merchants() => _merchants;
  @override
  List<OpsAlert> alerts() => _alerts;
  @override
  List<Ticket> tickets() => _tickets;
  @override
  List<OpsUser> users() => _users;
  @override
  List<int> fleetVolume() => _fleetVol;
}
