import 'api_client.dart';
import 'merchant_repository.dart';
import 'mock_data.dart';
import 'models.dart';

/// Live implementation of [MerchantRepository]. Fetches the tenant's data from
/// /api/v1 once (via [hydrate]) into in-memory caches, then serves the existing
/// synchronous screens unchanged. Selected by [merchantRepositoryProvider] when
/// USE_MOCK=false. FAQs and the report *definitions* stay bundled (no API surface).
class ApiMerchantRepository implements MerchantRepository {
  ApiMerchantRepository(this.api, this.tenantId);
  final ApiClient api;
  final String? tenantId;

  List<Branch> _branches = const [];
  List<Service> _services = const [];
  List<Convo> _convos = const [];
  List<Appt> _appts = const [];
  List<Holiday> _holidays = const [];
  List<int> _volume = const [];

  Future<void> hydrate() async {
    final q = tenantId != null ? {'tenant_id': tenantId} : null;

    // Branches (Clinic). Needs the tenant id — resolve from /auth/me scope if absent.
    if (tenantId != null) {
      final b = await api.get('/tenants/$tenantId/branches');
      _branches = [for (final m in (b['items'] as List)) _branch(m)];
    }

    final s = await api.get('/services', query: q);
    _services = [for (final m in (s['items'] as List)) _service(m)];

    final c = await api.get('/calls', query: q);
    _convos = [for (final m in (c['items'] as List)) _convo(m)];

    final a = await api.get('/appointments', query: q);
    _appts = [for (final m in (a['items'] as List)) _appt(m)];

    final st = await api.get('/settings', query: q);
    _holidays = [for (final m in ((st['holidays'] as List?) ?? const [])) _holiday(m)];

    try {
      final an = await api.get('/analytics/overview', query: q);
      _volume = [for (final v in ((an['call_volume'] as List?) ?? const [])) (v as num).toInt()];
    } catch (_) {
      _volume = kVol;
    }
    if (_volume.isEmpty) _volume = kVol;
    if (_branches.isEmpty) _branches = kBranches;
  }

  // ---- mapping ----
  Branch _branch(Map m) => Branch(
        id: (m['id']).hashCode,
        name: {'en': '${m['name']}', 'ar': '${m['name']}'},
        addr: {'en': '${m['address'] ?? ''}', 'ar': '${m['address'] ?? ''}'},
      );

  LMap _lmap(dynamic v, String fallback) {
    if (v is Map) return {'en': '${v['en'] ?? fallback}', 'ar': '${v['ar'] ?? v['en'] ?? fallback}'};
    return {'en': fallback, 'ar': fallback};
  }

  Service _service(Map m) => Service(
        id: '${m['id']}',
        en: '${m['en'] ?? m['name']}',
        ar: '${m['ar'] ?? m['name']}',
        cat: '${m['cat'] ?? ''}',
        price: (m['price'] as num?)?.toInt() ?? 0,
        dur: (m['dur'] as num?)?.toInt() ?? 30,
        about: _lmap(m['about'], '${m['description'] ?? ''}'),
        tiers: [
          for (final t in ((m['tiers'] as List?) ?? const []))
            Tier({'en': '${t['en'] ?? ''}', 'ar': '${t['ar'] ?? t['en'] ?? ''}'}, (t['price'] as num?)?.toInt() ?? 0)
        ],
        prep: _lmap(m['prep'], ''),
        after: _lmap(m['after'], ''),
      );

  Convo _convo(Map m) => Convo(
        name: '${m['name']}',
        phone: '${m['phone']}',
        time: '${m['time']}',
        tag: '${m['tag']}',
        lang: '${m['lang']}',
        summary: '${m['summary'] ?? ''}',
        treatment: m['treatment'] as String?,
        price: (m['price'] as num?)?.toInt(),
        sentiment: '${m['sentiment'] ?? ''}',
        dur: '${m['dur'] ?? '—'}',
        urgent: m['urgent'] == true,
      );

  Appt _appt(Map m) => Appt(
        name: '${m['name']}',
        svc: {'en': '${m['svc'] ?? ''}', 'ar': '${m['svc'] ?? ''}'},
        day: {'en': '${m['day'] ?? ''}', 'ar': '${m['day'] ?? ''}'},
        date: '${m['date'] ?? ''}',
        time: '${m['time'] ?? ''}',
        via: '${m['via'] ?? 'AI · Voice'}',
      );

  Holiday _holiday(Map m) => Holiday(
        name: {'en': '${m['name']}', 'ar': '${m['name']}'},
        date: {'en': '${m['date'] ?? ''}', 'ar': '${m['date'] ?? ''}'},
        closed: m['closed'] == true,
        hours: '${m['hours'] ?? ''}',
        upcoming: true,
      );

  // ---- interface (served from cache) ----
  @override
  List<Branch> branches() => _branches;
  @override
  List<Service> services() => _services;
  @override
  Service? serviceById(String id) {
    for (final s in _services) {
      if (s.id == id) return s;
    }
    return null;
  }

  @override
  List<Convo> conversations() => _convos;
  @override
  List<Faq> faqs() => kFaqs; // no API surface — bundled
  @override
  List<Appt> appointments() => _appts;
  @override
  List<Holiday> holidays() => _holidays;
  @override
  List<int> callVolume() => _volume;
  @override
  Map<String, List<Report>> reports() => kReports; // report definitions are static
}
