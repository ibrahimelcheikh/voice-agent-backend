/// Domain models for the PrimeOps operator console.
class Merchant {
  final int id;
  final String name;
  final String city;
  final String type;
  final String plan;
  final String status; // live | onboarding | paused
  final int calls;
  final int bookings;
  final int mrr;
  final int health;
  final List<String> langs;
  const Merchant({
    required this.id,
    required this.name,
    required this.city,
    required this.type,
    required this.plan,
    required this.status,
    required this.calls,
    required this.bookings,
    required this.mrr,
    required this.health,
    required this.langs,
  });
}

class OpsAlert {
  final int id;
  final String sev; // critical | warning | info
  final String title;
  final String merchant;
  final String time;
  final String body;
  const OpsAlert({
    required this.id,
    required this.sev,
    required this.title,
    required this.merchant,
    required this.time,
    required this.body,
  });
}

class Ticket {
  final String id;
  final String subject;
  final String merchant;
  final String status; // open | in_progress | resolved
  final String pri; // high | medium | low
  final String agent;
  final String time;
  const Ticket({
    required this.id,
    required this.subject,
    required this.merchant,
    required this.status,
    required this.pri,
    required this.agent,
    required this.time,
  });
}

class OpsUser {
  final int id;
  final String name;
  final String email;
  final String role;
  final bool active;
  const OpsUser({
    required this.id,
    required this.name,
    required this.email,
    required this.role,
    required this.active,
  });
}
