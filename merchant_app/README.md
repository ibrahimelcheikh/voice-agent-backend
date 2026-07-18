# AtlasPrimeX — Merchant Dashboard (Flutter)

Phase 2. A faithful Flutter re-creation of `02-merchant-dashboard.jsx` — the
bilingual (English ⇄ Arabic, full RTL) clinic dashboard. Targets **web and
mobile** from one codebase.

## What's inside

All screens from the design:

- **Overview** — greeting, revenue line, 3 KPIs, "Popular Times" bar chart, optimize tip, recent activity
- **Conversations** — searchable list, expandable transcripts (treatment/price, urgent transfer, sentiment, playback), date-range picker dialog
- **Services** — category tabs, featured card, service cards → **detail pages** (about, options & pricing tiers, prep, aftercare, book)
- **Reports** — Call Analytics + Bookings & Revenue groups → **per-report chart pages** (line / bar / donut / horizontal-bar)
- **Appointments** — upcoming bookings with date chips and channel tags
- **Settings** — tabs **General / Voice / Booking / FAQ**, including the **Holiday Hours manager** (add/remove, closed-all-day vs special hours), **Open & Closed greetings**, **Temporary Closure**, voice picker + speed/ambience sliders, Cal.com + SMS toggles, FAQ accordion
- **Multi-branch switcher** (top bar) and **EN⇄Arabic toggle** with full RTL mirroring

## Architecture

| Layer | Location | Notes |
|---|---|---|
| Design tokens | `lib/theme/tokens.dart` | Colors/shadows identical to the design's `C` map |
| Copy (EN/AR) | `lib/l10n/strings.dart` | 1:1 with the design's `T` object |
| Models | `lib/data/models.dart` | Localized `{en, ar}` fields |
| Mock data | `lib/data/mock_data.dart` | Verbatim from the design file |
| Repository | `lib/data/merchant_repository.dart` | `MerchantRepository` interface + `MockMerchantRepository`. Phase 4 adds an API impl behind the `USE_MOCK` flag — screens never change |
| State | `lib/state/app_state.dart` | Riverpod providers (language, branch, nav, tabs, detail views) |
| Widgets | `lib/widgets/` | Shared UI (`ui.dart`) + charts (`charts.dart`, fl_chart) |
| Screens | `lib/screens/` | One file per section |

- **State management:** Riverpod
- **Charts:** fl_chart (line / bar / donut); the report "by treatment" breakdown uses the design's exact horizontal progress-bar style
- **Fonts:** google_fonts — Poppins (English) and Noto Sans Arabic (Arabic)

## Run it

```bash
cd merchant_app
flutter pub get

# Web (Chrome)
flutter run -d chrome

# Mobile (with an emulator/device attached)
flutter run

# Production web build (CanvasKit bundled locally, no CDN needed)
flutter build web --no-web-resources-cdn
# output: build/web/  — serve with any static server
```

> Requires Flutter 3.44+ (Dart 3.12+). The app runs entirely on bundled mock
> data, so no backend is needed to see every screen. Phase 4 wires the
> repository layer to the live `/api/v1` backend behind `--dart-define=USE_MOCK=false`.

Railway deploy config for this app is added in **Phase 4** (alongside the API),
so all three apps ship together.
