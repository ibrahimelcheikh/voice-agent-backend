import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/ops_repository.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import 'overview.dart';
import 'merchants.dart';
import 'onboarding.dart';
import 'prompts.dart';
import 'alerts.dart';
import 'tickets.dart';
import 'analytics.dart';
import 'users.dart';
import 'merchant_view.dart';

const _nav = <List<dynamic>>[
  ['overview', Icons.grid_view_rounded, 'Overview'],
  ['merchants', Icons.storefront_outlined, 'Merchants'],
  ['onboarding', Icons.person_add_alt_1_outlined, 'Onboarding'],
  ['prompts', Icons.auto_awesome_outlined, 'Agent Config'],
  ['alerts', Icons.notifications_none, 'Alerts'],
  ['tickets', Icons.confirmation_number_outlined, 'Tickets'],
  ['analytics', Icons.pie_chart_outline, 'Analytics'],
  ['users', Icons.group_outlined, 'Users'],
];

class OpsShell extends ConsumerWidget {
  const OpsShell({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final desktop = MediaQuery.of(context).size.width >= 900;
    final nav = ref.watch(navProvider);
    final merchantView = ref.watch(merchantViewProvider);

    if (merchantView) return const MerchantView();

    final body = Container(
      constraints: const BoxConstraints(maxWidth: 1080),
      padding: EdgeInsets.all(desktop ? 32 : 16),
      child: _screenFor(nav, desktop),
    );

    if (desktop) {
      return Scaffold(
        backgroundColor: AppColors.bg,
        body: Row(
          children: [
            SizedBox(width: 250, child: _Sidebar(desktop: true)),
            Expanded(
              child: SingleChildScrollView(
                child: Center(child: body),
              ),
            ),
          ],
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.bg,
      drawer: Drawer(width: 270, backgroundColor: AppColors.card, child: _Sidebar(desktop: false)),
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _MobileTopBar(),
            Expanded(child: SingleChildScrollView(child: Center(child: body))),
          ],
        ),
      ),
    );
  }

  Widget _screenFor(String nav, bool desktop) {
    switch (nav) {
      case 'merchants':
        return const MerchantsScreen();
      case 'onboarding':
        return const OnboardingScreen();
      case 'prompts':
        return const PromptsScreen();
      case 'alerts':
        return const AlertsScreen();
      case 'tickets':
        return const TicketsScreen();
      case 'analytics':
        return const AnalyticsScreen();
      case 'users':
        return const UsersScreen();
      case 'overview':
      default:
        return const OpsOverviewScreen();
    }
  }
}

class Brand extends StatelessWidget {
  const Brand({super.key});
  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Image.asset('assets/logo-mark.png', width: 32, height: 32),
        const SizedBox(width: 9),
        Text.rich(TextSpan(
          style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18, letterSpacing: -0.4),
          children: const [
            TextSpan(text: 'Prime', style: TextStyle(color: AppColors.ink)),
            TextSpan(text: 'Ops', style: TextStyle(color: AppColors.blue)),
          ],
        )),
      ],
    );
  }
}

class _Sidebar extends ConsumerWidget {
  final bool desktop;
  const _Sidebar({required this.desktop});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final nav = ref.watch(navProvider);
    final repo = ref.read(opsRepositoryProvider);
    final alertCount = repo.alerts().where((a) => a.sev != 'info').length;
    final openTickets = repo.tickets().where((t) => t.status != 'resolved').length;

    return Container(
      height: double.infinity,
      decoration: const BoxDecoration(
        color: AppColors.card,
        border: Border(right: BorderSide(color: AppColors.line)),
      ),
      padding: const EdgeInsets.all(18),
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Brand(),
                if (!desktop)
                  InkWell(onTap: () => Navigator.of(context).pop(), child: const Icon(Icons.close, size: 22, color: AppColors.ink)),
              ],
            ),
            const SizedBox(height: 20),
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  for (final item in _nav)
                    _navItem(context, ref, item[0] as String, item[1] as IconData, item[2] as String, nav == item[0],
                        item[0] == 'alerts' ? alertCount : item[0] == 'tickets' ? openTickets : 0,
                        item[0] == 'alerts' ? AppColors.rose : AppColors.blue),
                ],
              ),
            ),
            const SizedBox(height: 12),
            // View as merchant
            InkWell(
              onTap: () => ref.read(merchantViewProvider.notifier).state = true,
              borderRadius: BorderRadius.circular(12),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: AppColors.card, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.line, width: 1.5)),
                child: Row(mainAxisAlignment: MainAxisAlignment.center, children: const [
                  Icon(Icons.visibility_outlined, size: 18, color: AppColors.blue),
                  SizedBox(width: 8),
                  Text('View as merchant', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14, color: AppColors.ink)),
                ]),
              ),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(color: AppColors.cardAlt, borderRadius: BorderRadius.circular(12)),
              child: Row(children: [
                Container(
                  width: 36, height: 36,
                  decoration: const BoxDecoration(gradient: LinearGradient(colors: [AppColors.blue, AppColors.blueDeep]), shape: BoxShape.circle),
                  alignment: Alignment.center,
                  child: const Text('I', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15)),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text('Ibrahim El Cheikh', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: AppColors.ink)),
                      Text('Owner', style: TextStyle(color: AppColors.sub, fontSize: 12)),
                    ],
                  ),
                ),
              ]),
            ),
          ],
        ),
      ),
    );
  }

  Widget _navItem(BuildContext context, WidgetRef ref, String k, IconData icon, String label, bool on, int badge, Color badgeColor) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          goTo(ref, k);
          if (!desktop) Navigator.of(context).pop();
        },
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 11),
          decoration: BoxDecoration(color: on ? AppColors.blueSoft : Colors.transparent, borderRadius: BorderRadius.circular(12)),
          child: Row(children: [
            Icon(icon, size: 20, color: on ? AppColors.blueDeep : AppColors.sub),
            const SizedBox(width: 13),
            Text(label, style: TextStyle(color: on ? AppColors.blueDeep : AppColors.ink, fontWeight: on ? FontWeight.w800 : FontWeight.w600, fontSize: 15)),
            if (badge > 0) ...[
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 1),
                decoration: BoxDecoration(color: badgeColor, borderRadius: BorderRadius.circular(999)),
                child: Text('$badge', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w800)),
              ),
            ],
          ]),
        ),
      ),
    );
  }
}

class _MobileTopBar extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      decoration: const BoxDecoration(color: AppColors.card, border: Border(bottom: BorderSide(color: AppColors.line))),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(children: [
        Builder(
          builder: (context) => InkWell(
            onTap: () => Scaffold.of(context).openDrawer(),
            borderRadius: BorderRadius.circular(999),
            child: Container(
              width: 44, height: 44,
              decoration: const BoxDecoration(color: AppColors.cardAlt, shape: BoxShape.circle),
              child: const Icon(Icons.menu, size: 20, color: AppColors.ink),
            ),
          ),
        ),
        const SizedBox(width: 12),
        const Brand(),
        const Spacer(),
        InkWell(
          onTap: () => ref.read(merchantViewProvider.notifier).state = true,
          borderRadius: BorderRadius.circular(999),
          child: Container(
            height: 40,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(color: AppColors.blueSoft, borderRadius: BorderRadius.circular(999)),
            child: Row(mainAxisSize: MainAxisSize.min, children: const [
              Icon(Icons.visibility_outlined, size: 16, color: AppColors.blueDeep),
              SizedBox(width: 6),
              Text('Merchant', style: TextStyle(color: AppColors.blueDeep, fontWeight: FontWeight.w800, fontSize: 13)),
            ]),
          ),
        ),
      ]),
    );
  }
}
