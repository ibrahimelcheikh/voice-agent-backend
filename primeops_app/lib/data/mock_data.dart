import 'models.dart';

/// Mock datasets copied verbatim from 03-primeops-console.jsx.

const List<Merchant> kMerchants = [
  Merchant(id: 1, name: 'Divinia Clinic', city: 'Riyadh', type: 'Med Spa', plan: 'Premium', status: 'live', calls: 1540, bookings: 243, mrr: 250, health: 98, langs: ['ar', 'en']),
  Merchant(id: 2, name: 'Lumière Aesthetics', city: 'Jeddah', type: 'Clinic', plan: 'Pro', status: 'live', calls: 880, bookings: 141, mrr: 200, health: 95, langs: ['ar', 'en']),
  Merchant(id: 3, name: 'Downtown Dental', city: 'Dubai', type: 'Dental', plan: 'Pro', status: 'live', calls: 1210, bookings: 198, mrr: 200, health: 91, langs: ['ar', 'en']),
  Merchant(id: 4, name: 'Nova Skin Bar', city: 'Riyadh', type: 'Med Spa', plan: 'Starter', status: 'onboarding', calls: 0, bookings: 0, mrr: 150, health: 0, langs: ['ar']),
  Merchant(id: 5, name: 'Cedar Wellness', city: 'Doha', type: 'Clinic', plan: 'Pro', status: 'live', calls: 640, bookings: 88, mrr: 200, health: 87, langs: ['ar', 'en']),
  Merchant(id: 6, name: 'Pearl Derma', city: 'Kuwait City', type: 'Dermatology', plan: 'Starter', status: 'paused', calls: 210, bookings: 24, mrr: 150, health: 40, langs: ['ar']),
];

const List<OpsAlert> kAlerts = [
  OpsAlert(id: 1, sev: 'critical', title: 'Voice agent not registering', merchant: 'Pearl Derma', time: '8 min ago', body: 'LiveKit worker for Pearl Derma stopped responding to health checks.'),
  OpsAlert(id: 2, sev: 'warning', title: 'Cal.com sync delayed', merchant: 'Cedar Wellness', time: '42 min ago', body: 'Booking sync latency above 30s. Calendar writes are queuing.'),
  OpsAlert(id: 3, sev: 'warning', title: 'High after-hours volume', merchant: 'Downtown Dental', time: '1 hr ago', body: '3x normal after-hours calls. Consider reviewing closed-hours greeting.'),
  OpsAlert(id: 4, sev: 'info', title: 'Urgent call escalated', merchant: 'Divinia Clinic', time: '2 hrs ago', body: 'Filler-swelling call transferred to on-call clinician. Resolved.'),
];

const List<Ticket> kTickets = [
  Ticket(id: 'T-1042', subject: 'Add Arabic voice to my number', merchant: 'Nova Skin Bar', status: 'open', pri: 'high', agent: '—', time: '20 min ago'),
  Ticket(id: 'T-1041', subject: 'Wrong price quoted for laser', merchant: 'Downtown Dental', status: 'in_progress', pri: 'high', agent: 'Layla', time: '1 hr ago'),
  Ticket(id: 'T-1039', subject: 'Reminder SMS not sending', merchant: 'Cedar Wellness', status: 'in_progress', pri: 'medium', agent: 'Sami', time: '3 hrs ago'),
  Ticket(id: 'T-1035', subject: 'Request: WhatsApp channel', merchant: 'Lumière Aesthetics', status: 'open', pri: 'medium', agent: '—', time: '5 hrs ago'),
  Ticket(id: 'T-1030', subject: 'Update clinic hours for Eid', merchant: 'Divinia Clinic', status: 'resolved', pri: 'low', agent: 'Layla', time: '1 day ago'),
];

const List<OpsUser> kUsers = [
  OpsUser(id: 1, name: 'Ibrahim El Cheikh', email: 'ibrahim@primetech.ai', role: 'Owner', active: true),
  OpsUser(id: 2, name: 'Layla Haddad', email: 'layla@primetech.ai', role: 'Support Lead', active: true),
  OpsUser(id: 3, name: 'Sami Nasr', email: 'sami@primetech.ai', role: 'Onboarding', active: true),
  OpsUser(id: 4, name: 'Rana Aziz', email: 'rana@primetech.ai', role: 'Support', active: true),
  OpsUser(id: 5, name: 'Omar Khoury', email: 'omar@primetech.ai', role: 'Support', active: false),
];

const List<int> kFleetVol = [
  42, 55, 48, 61, 52, 70, 120, 66, 58, 72, 60, 80, 54, 128, //
  63, 68, 59, 50, 44, 96, 82, 64, 70, 55, 78, 45, 140, 88
];
