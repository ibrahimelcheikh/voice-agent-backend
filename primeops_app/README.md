# AtlasPrimeX — PrimeOps Console (Flutter web)

Phase 3. A faithful Flutter re-creation of `03-primeops-console.jsx` — the
internal operator console. **Responsive**: a persistent sidebar at ≥900px, a
drawer + mobile top bar below.

## Sections (all 7 + view-as-merchant)

- **Overview** — fleet KPIs, fleet call-volume line chart, active alerts + open tickets summaries
- **Merchants** — searchable grid with health bars → **merchant detail** (KPIs + configuration)
- **Onboarding** — 5-step wizard (Business → Channels → Hours → Services → Review)
- **Agent Config** — per-merchant system prompt (auto-templated), voice selection, guardrails
- **Alerts** — severity filters (All/Critical/Warning/Info), colored left border + badges
- **Tickets** — table on desktop / cards on mobile, status filters, priority colors
- **Analytics** — cross-merchant KPIs, calls-by-merchant bars, booking-channel donut, fleet line
- **Users** — team list with role/status pills + add-user form
- **View as merchant** — opens a compact merchant-app preview for a tenant, with its own EN⇄Arabic toggle

Sidebar badges show non-info alert count and open-ticket count, exactly as the design.

## Architecture (same pattern as the merchant app)

| Layer | Location |
|---|---|
| Design tokens | `lib/theme/tokens.dart` (identical to the shared tokens) |
| Models | `lib/data/models.dart` |
| Mock data | `lib/data/mock_data.dart` (verbatim from the design file) |
| Repository | `lib/data/ops_repository.dart` — `OpsRepository` + `MockOpsRepository`, behind `USE_MOCK`. PrimeOps sees **all** tenants |
| State | `lib/state/app_state.dart` — Riverpod providers + status/severity maps |
| Widgets / charts | `lib/widgets/` (fl_chart) |
| Screens | `lib/screens/` (one per section) |

- **State:** Riverpod · **Charts:** fl_chart · **Font:** Poppins (self-hosted; Noto Sans Arabic bundled for the Arabic merchant-view toggle)

## Run it

```bash
cd primeops_app
flutter pub get
flutter run -d chrome                        # dev
flutter build web --no-web-resources-cdn     # production → build/web/
```

Runs entirely on mock data. Phase 4 wires the repository to the live `/api/v1`
backend behind `--dart-define=USE_MOCK=false` (PrimeOps scoped to all tenants).
Railway deploy config for the Flutter apps ships in Phase 4.

Optional deep links: `?nav=merchants&merchant=1`, `?view=merchant&mvlang=ar`,
`?nav=onboarding&step=3`, `?nav=users&adduser=1`.
