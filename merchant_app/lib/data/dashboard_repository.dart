import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'merchant_repository.dart';
import 'mock_data.dart';
import 'models.dart';

/// Real-data repository for the merchant dashboard. Fetches Overview counts,
/// Conversations and Appointments from the no-auth /api/v1/tenants/{slug}/… endpoints
/// and serves the existing synchronous screens. Reports/Settings/Services stay on the
/// bundled mock data (no API surface for them yet), so the app always renders fully.
class DashboardMerchantRepository implements MerchantRepository {
  DashboardMerchantRepository(this.api, this.slug);
  final ApiClient api;
  final String slug;

  List<Convo> _convos = const [];
  List<Appt> _appts = const [];
  List<Service> _services = const [];

  /// Overview KPI counts from /summary.
  Map<String, int> counts = const {'calls': 0, 'appointments': 0, 'afterHours': 0};

  /// Settings the agent speaks: per-day hours (keys sat..fri) + greetings.
  Map<String, String> hoursMap = const {};
  String? openGreeting;
  String? closedGreeting;

  // ---- reads: real where we have it, mock for the rest ----
  @override
  List<Branch> branches() => kBranches;
  @override
  List<Service> services() => _services.isNotEmpty ? _services : kServices;
  @override
  Service? serviceById(String id) {
    for (final s in services()) {
      if (s.id == id) return s;
    }
    return null;
  }

  @override
  List<Convo> conversations() => _convos;
  @override
  List<Faq> faqs() => kFaqs;
  @override
  List<Appt> appointments() => _appts;
  @override
  List<Holiday> holidays() => kHolidays;
  @override
  List<int> callVolume() => kVol;
  @override
  Map<String, List<Report>> reports() => kReports;

  // ---- hydrate ----
  Future<void> hydrate() async {
    final s = await api.get('/tenants/$slug/summary') as Map;
    counts = {
      'calls': _int(s['calls_this_month']),
      'appointments': _int(s['appointments_booked']),
      'afterHours': _int(s['after_hours_calls']),
    };
    final c = await api.get('/tenants/$slug/conversations') as Map;
    _convos = [for (final m in (c['items'] as List? ?? const [])) _convo(m as Map)];
    final a = await api.get('/tenants/$slug/appointments') as Map;
    _appts = [for (final m in (a['items'] as List? ?? const [])) _appt(m as Map)];
    final sv = await api.get('/tenants/$slug/services') as Map;
    _services = [for (final m in (sv['items'] as List? ?? const [])) _service(m as Map)];
    final set = await api.get('/tenants/$slug/settings') as Map;
    hoursMap = {
      for (final e in ((set['hours'] as Map?) ?? const {}).entries) '${e.key}': '${e.value}'
    };
    openGreeting = set['open_greeting']?.toString();
    closedGreeting = set['closed_greeting']?.toString();
  }

  Future<void> updateService(String id, {String? name, int? price}) async {
    await api.patch('/tenants/$slug/services/$id', {
      if (name != null) 'name': name,
      if (price != null) 'price': price,
    });
    await hydrate();
  }

  Future<void> updateHours(Map<String, String> hours) async {
    await api.put('/tenants/$slug/hours', {'hours': hours});
    await hydrate();
  }

  Future<void> updateGreetings({String? open, String? closed}) async {
    await api.put('/tenants/$slug/greetings', {
      if (open != null) 'open_greeting': open,
      if (closed != null) 'closed_greeting': closed,
    });
    await hydrate();
  }

  // ---- mutations (each re-hydrates so the UI reflects the truth) ----
  Future<void> createAppointment({
    required String name,
    required String phone,
    String? service,
    required String date,
    required String time,
  }) async {
    await api.post('/tenants/$slug/appointments', {
      'name': name,
      'phone': phone,
      'service': service,
      'date': date,
      'time': time,
    });
    await hydrate();
  }

  Future<void> modifyAppointment(String id,
      {String? date, String? time, String? service, String? status}) async {
    await api.patch('/tenants/$slug/appointments/$id', {
      if (date != null) 'date': date,
      if (time != null) 'time': time,
      if (service != null) 'service': service,
      if (status != null) 'status': status,
    });
    await hydrate();
  }

  Future<void> deleteAppointment(String id) async {
    await api.delete('/tenants/$slug/appointments/$id');
    await hydrate();
  }

  // ---- mapping ----
  Convo _convo(Map m) {
    final booking = m['booking'] as Map?;
    final urgent = m['urgent'] == true;
    return Convo(
      name: (m['caller_number'] ?? 'Caller').toString(),
      phone: (m['caller_number'] ?? '').toString(),
      time: _shortTime(m['time']?.toString()),
      tag: booking != null ? 'booked' : 'call',
      lang: (m['language'] ?? 'en').toString(),
      summary: (m['summary'] ?? '').toString(),
      treatment: booking?['service']?.toString(),
      sentiment: urgent ? 'Urgent' : 'Positive',
      dur: _dur(m['duration_seconds']),
      urgent: urgent,
      transcript: (m['transcript'] ?? '').toString(),
    );
  }

  Appt _appt(Map m) {
    final svc = (m['service'] ?? '').toString();
    return Appt(
      id: m['id']?.toString(),
      name: (m['name'] ?? '').toString(),
      svc: {'en': svc, 'ar': svc},
      day: _weekday(m['date']?.toString()),
      date: (m['date'] ?? '').toString(),
      time: (m['time'] ?? '').toString(),
      via: (m['via'] ?? 'voice').toString(),
      status: m['status']?.toString(),
      phone: m['phone']?.toString(),
      price: m['price']?.toString(),
    );
  }

  Service _service(Map m) {
    final det = (m['details'] is Map) ? (m['details'] as Map) : const {};
    LMap lm(dynamic v) => v is Map
        ? {'en': (v['en'] ?? '').toString(), 'ar': (v['ar'] ?? '').toString()}
        : {'en': '', 'ar': ''};
    final tiers = <Tier>[];
    for (final tr in (det['tiers'] as List? ?? const [])) {
      if (tr is Map) {
        tiers.add(Tier(
          {'en': (tr['en'] ?? '').toString(), 'ar': (tr['ar'] ?? '').toString()},
          _int(tr['price']),
        ));
      }
    }
    final name = (m['name'] ?? '').toString();
    return Service(
      id: (m['id'] ?? '').toString(),
      en: name,
      ar: (det['ar'] ?? name).toString(),
      cat: (m['category'] ?? '').toString(),
      price: _int(m['price']),
      dur: _int(m['duration_minutes']),
      about: lm(det['about']),
      tiers: tiers,
      prep: lm(det['prep']),
      after: lm(det['after']),
    );
  }

  int _int(dynamic v) => (v is num) ? v.toInt() : 0;

  String _shortTime(String? iso) {
    if (iso == null || iso.isEmpty) return '';
    final d = DateTime.tryParse(iso);
    if (d == null) return iso;
    final l = d.toLocal();
    final h = l.hour % 12 == 0 ? 12 : l.hour % 12;
    final ap = l.hour < 12 ? 'AM' : 'PM';
    return '$h:${l.minute.toString().padLeft(2, '0')} $ap';
  }

  String _dur(dynamic secs) {
    final s = (secs is num) ? secs.toInt() : 0;
    return '${(s ~/ 60).toString().padLeft(2, '0')}:${(s % 60).toString().padLeft(2, '0')}';
  }

  LMap _weekday(String? date) {
    final d = (date == null || date.isEmpty) ? null : DateTime.tryParse(date);
    if (d == null) return {'en': '', 'ar': ''};
    const en = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const ar = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد'];
    return {'en': en[d.weekday - 1], 'ar': ar[d.weekday - 1]};
  }
}

/// The active real-data repository (null in mock mode). Screens use it for mutations
/// (create/modify/delete) and Overview counts.
final dashboardRepoProvider = StateProvider<DashboardMerchantRepository?>((ref) => null);

/// Bumped after any refresh/mutation to force the data screens to rebuild.
final refreshTickProvider = StateProvider<int>((ref) => 0);
