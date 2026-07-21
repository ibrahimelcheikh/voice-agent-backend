/// Domain models for the merchant dashboard.
///
/// Localized fields are stored as `{ "en": ..., "ar": ... }` maps and resolved
/// with [loc]. This mirrors the design file exactly so screens stay faithful.
typedef LMap = Map<String, String>;

String loc(LMap m, String lang) => m[lang] ?? m['en'] ?? '';

class Branch {
  final int id;
  final LMap name;
  final LMap addr;
  const Branch({required this.id, required this.name, required this.addr});
}

class Tier {
  final LMap label; // {en, ar}
  final int price;
  const Tier(this.label, this.price);
}

class Service {
  final String id;
  final String en;
  final String ar;
  final String cat;
  final int price;
  final int dur;
  final LMap about;
  final List<Tier> tiers;
  final LMap prep;
  final LMap after;
  const Service({
    required this.id,
    required this.en,
    required this.ar,
    required this.cat,
    required this.price,
    required this.dur,
    required this.about,
    required this.tiers,
    required this.prep,
    required this.after,
  });

  String name(String lang) => lang == 'ar' ? ar : en;
}

class Convo {
  final String name;
  final String phone;
  final String time;
  final String tag; // booked | call | msg
  final String lang; // ar | en
  final String summary;
  final String? treatment;
  final int? price;
  final String sentiment;
  final String dur;
  final bool urgent;
  const Convo({
    required this.name,
    required this.phone,
    required this.time,
    required this.tag,
    required this.lang,
    required this.summary,
    this.treatment,
    this.price,
    required this.sentiment,
    required this.dur,
    this.urgent = false,
  });
}

class Faq {
  final String en;
  final String ar;
  final String aEn;
  final String aAr;
  const Faq(this.en, this.ar, this.aEn, this.aAr);
}

class Appt {
  final String name;
  final LMap svc;
  final LMap day;
  final String date;
  final String time;
  final String via;
  final String? id;      // backend appointment id (real data) — null for mock rows
  final String? status;  // booked | confirmed | rescheduled | cancelled | completed
  const Appt({
    required this.name,
    required this.svc,
    required this.day,
    required this.date,
    required this.time,
    required this.via,
    this.id,
    this.status,
  });
}

class Holiday {
  final LMap name;
  final LMap date;
  final bool closed;
  final String hours;
  final bool upcoming;
  const Holiday({
    required this.name,
    required this.date,
    required this.closed,
    required this.hours,
    required this.upcoming,
  });

  Holiday copy() => Holiday(
        name: name,
        date: date,
        closed: closed,
        hours: hours,
        upcoming: upcoming,
      );
}

class Report {
  final String id;
  final String en;
  final String ar;
  final String chart; // line | bar | donut | hbar
  final String descEn;
  final String descAr;
  const Report({
    required this.id,
    required this.en,
    required this.ar,
    required this.chart,
    required this.descEn,
    required this.descAr,
  });

  String title(String lang) => lang == 'ar' ? ar : en;
  String desc(String lang) => lang == 'ar' ? descAr : descEn;
}
