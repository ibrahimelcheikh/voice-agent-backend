import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/dashboard_repository.dart';
import '../data/merchant_repository.dart';
import '../data/models.dart';
import '../l10n/strings.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import 'overview.dart';
import 'convos.dart';
import 'services.dart';
import 'reports.dart';
import 'appts.dart';
import 'settings.dart';
import 'support.dart';

const _navKeys = ['overview', 'convos', 'services', 'reports', 'appts', 'settings', 'support'];

IconData navIcon(String k) => const {
      'overview': Icons.home_outlined,
      'convos': Icons.call_outlined,
      'services': Icons.auto_awesome_outlined,
      'reports': Icons.pie_chart_outline,
      'appts': Icons.calendar_today_outlined,
      'settings': Icons.settings_outlined,
      'support': Icons.help_outline,
    }[k]!;

class MerchantShell extends ConsumerWidget {
  const MerchantShell({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(languageProvider);
    final nav = ref.watch(navProvider);

    return Scaffold(
      backgroundColor: AppColors.bg,
      drawer: _NavDrawer(),
      drawerEnableOpenDragGesture: true,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            const _TopBar(),
            Expanded(
              child: RefreshIndicator(
                onRefresh: () => _refresh(ref),
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(16),
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 640),
                      child: KeyedSubtree(
                        key: ValueKey('$nav-$lang'),
                        child: _screenFor(nav),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Pull-to-refresh: re-fetch live data (no-op in mock mode) and rebuild screens.
  Future<void> _refresh(WidgetRef ref) async {
    final repo = ref.read(dashboardRepoProvider);
    if (repo != null) {
      try {
        await repo.hydrate();
      } catch (_) {}
    }
    ref.read(refreshTickProvider.notifier).state++;
  }

  Widget _screenFor(String nav) {
    switch (nav) {
      case 'convos':
        return const ConvosScreen();
      case 'services':
        return const ServicesScreen();
      case 'reports':
        return const ReportsScreen();
      case 'appts':
        return const ApptsScreen();
      case 'settings':
        return const SettingsScreen();
      case 'support':
        return const SupportScreen();
      case 'overview':
      default:
        return const OverviewScreen();
    }
  }
}

/// Brand lockup — real AtlasPrimeX logo mark + wordmark.
class Brand extends StatelessWidget {
  final double size;
  const Brand({super.key, this.size = 34});
  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Image.asset('assets/logo-mark.png', width: size, height: size),
        const SizedBox(width: 9),
        Text.rich(
          TextSpan(
            style: TextStyle(fontWeight: FontWeight.w900, fontSize: size * 0.59, letterSpacing: -0.4),
            children: const [
              TextSpan(text: 'Atlas', style: TextStyle(color: AppColors.ink)),
              TextSpan(text: 'Prime', style: TextStyle(color: AppColors.blue)),
              TextSpan(text: 'X', style: TextStyle(color: AppColors.blueDeep)),
            ],
          ),
        ),
      ],
    );
  }
}

class _TopBar extends ConsumerWidget {
  const _TopBar();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(languageProvider);
    final rtl = lang == 'ar';
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.card,
        border: Border(bottom: BorderSide(color: AppColors.line)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Builder(
            builder: (context) => InkWell(
              onTap: () => Scaffold.of(context).openDrawer(),
              borderRadius: BorderRadius.circular(999),
              child: Container(
                width: 44,
                height: 44,
                decoration: const BoxDecoration(color: AppColors.cardAlt, shape: BoxShape.circle),
                child: const Icon(Icons.menu, size: 20, color: AppColors.ink),
              ),
            ),
          ),
          const SizedBox(width: 12),
          const Expanded(child: BranchSwitcher()),
          const SizedBox(width: 12),
          InkWell(
            onTap: () => ref.read(languageProvider.notifier).state = rtl ? 'en' : 'ar',
            borderRadius: BorderRadius.circular(999),
            child: Container(
              height: 44,
              padding: const EdgeInsets.symmetric(horizontal: 14),
              decoration: BoxDecoration(color: AppColors.blueSoft, borderRadius: BorderRadius.circular(999)),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.language, size: 17, color: AppColors.blueDeep),
                  const SizedBox(width: 7),
                  Text(rtl ? 'EN' : 'ع',
                      style: const TextStyle(color: AppColors.blueDeep, fontWeight: FontWeight.w800, fontSize: 14)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Multi-branch switcher with an anchored dropdown (design's branch selector).
class BranchSwitcher extends ConsumerStatefulWidget {
  const BranchSwitcher({super.key});
  @override
  ConsumerState<BranchSwitcher> createState() => _BranchSwitcherState();
}

class _BranchSwitcherState extends ConsumerState<BranchSwitcher> {
  final _link = LayerLink();
  final _controller = OverlayPortalController();

  @override
  Widget build(BuildContext context) {
    final lang = ref.watch(languageProvider);
    final s = S.of(lang);
    final rtl = lang == 'ar';
    final branch = ref.watch(branchProvider);
    final branches = ref.read(merchantRepositoryProvider).branches();

    return CompositedTransformTarget(
      link: _link,
      child: OverlayPortal(
        controller: _controller,
        overlayChildBuilder: (context) {
          return Stack(children: [
            // backdrop to dismiss
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: _controller.hide,
                child: const SizedBox.shrink(),
              ),
            ),
            CompositedTransformFollower(
              link: _link,
              targetAnchor: Alignment.bottomLeft,
              followerAnchor: Alignment.topLeft,
              offset: const Offset(0, 8),
              child: Directionality(
                textDirection: s.dir,
                child: Align(
                  alignment: rtl ? Alignment.topRight : Alignment.topLeft,
                  child: Material(
                    color: Colors.transparent,
                    child: ConstrainedBox(
                      constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width - 32, minWidth: 260),
                      child: Container(
                        decoration: BoxDecoration(
                          color: AppColors.card,
                          borderRadius: BorderRadius.circular(20),
                          boxShadow: const [BoxShadow(color: Color(0x2E1B2431), blurRadius: 40, offset: Offset(0, 12))],
                        ),
                        clipBehavior: Clip.antiAlias,
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            for (int i = 0; i < branches.length; i++)
                              _branchRow(branches[i], i > 0, branch.id == branches[i].id, s, rtl),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ]);
        },
        child: InkWell(
          onTap: _controller.toggle,
          borderRadius: BorderRadius.circular(999),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
            decoration: BoxDecoration(color: AppColors.cardAlt, borderRadius: BorderRadius.circular(999)),
            child: Row(
              children: [
                Expanded(
                  child: Text(loc(branch.name, lang),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15, color: AppColors.ink)),
                ),
                const Icon(Icons.keyboard_arrow_down, size: 18, color: AppColors.sub),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _branchRow(Branch b, bool border, bool on, S s, bool rtl) {
    return InkWell(
      onTap: () {
        ref.read(branchProvider.notifier).state = b;
        _controller.hide();
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        decoration: BoxDecoration(
          color: on ? AppColors.amberSoft : Colors.transparent,
          border: border ? const Border(top: BorderSide(color: AppColors.line)) : null,
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(loc(b.name, s.lang),
                            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: AppColors.ink)),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                        decoration: BoxDecoration(color: AppColors.greenSoft, borderRadius: BorderRadius.circular(999)),
                        child: Text(s.v('activeShort'),
                            style: const TextStyle(color: AppColors.green, fontSize: 10.5, fontWeight: FontWeight.w700)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(loc(b.addr, s.lang), style: const TextStyle(color: AppColors.sub, fontSize: 13, height: 1.4)),
                ],
              ),
            ),
            if (on) const Padding(padding: EdgeInsets.only(top: 2), child: Icon(Icons.check, size: 20, color: AppColors.ink)),
          ],
        ),
      ),
    );
  }
}

class _NavDrawer extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(languageProvider);
    final s = S.of(lang);
    final rtl = lang == 'ar';
    final nav = ref.watch(navProvider);
    final branch = ref.watch(branchProvider);

    return Drawer(
      backgroundColor: AppColors.card,
      width: 300,
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Brand(),
                  InkWell(
                    onTap: () => Navigator.of(context).pop(),
                    child: const Icon(Icons.close, size: 22, color: AppColors.ink),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              for (final k in _navKeys) _navItem(context, ref, k, nav == k, s, rtl),
              const Spacer(),
              // Active status
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
                decoration: BoxDecoration(color: AppColors.greenSoft, borderRadius: BorderRadius.circular(14)),
                child: Row(
                  children: [
                    Container(width: 10, height: 10, decoration: const BoxDecoration(color: AppColors.green, shape: BoxShape.circle)),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(s.v('active'),
                          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: AppColors.ink)),
                    ),
                    const Icon(Icons.pause, size: 16, color: AppColors.amber),
                  ],
                ),
              ),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(color: AppColors.cardAlt, borderRadius: BorderRadius.circular(14)),
                child: Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: const BoxDecoration(
                        gradient: LinearGradient(colors: [AppColors.blue, AppColors.blueDeep]),
                        shape: BoxShape.circle,
                      ),
                      alignment: Alignment.center,
                      child: const Text('D', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(loc(branch.name, lang),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14, color: AppColors.ink)),
                          Text(s.v('saudiArabia'), style: const TextStyle(color: AppColors.sub, fontSize: 12.5)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _navItem(BuildContext context, WidgetRef ref, String k, bool on, S s, bool rtl) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 3),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () {
          goTo(ref, k);
          Navigator.of(context).pop();
        },
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
          decoration: BoxDecoration(
            color: on ? AppColors.blueSoft : Colors.transparent,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Row(
            children: [
              Icon(navIcon(k), size: 21, color: on ? AppColors.blueDeep : AppColors.sub),
              const SizedBox(width: 14),
              Text(s.nav(k),
                  style: TextStyle(
                      color: on ? AppColors.blueDeep : AppColors.ink,
                      fontWeight: on ? FontWeight.w800 : FontWeight.w600,
                      fontSize: 16)),
              if (k == 'services') ...[
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                  decoration: BoxDecoration(color: AppColors.greenSoft, borderRadius: BorderRadius.circular(999)),
                  child: Row(mainAxisSize: MainAxisSize.min, children: const [
                    Icon(Icons.auto_awesome, size: 12, color: AppColors.green),
                    SizedBox(width: 4),
                    Text('New', style: TextStyle(color: AppColors.green, fontSize: 11, fontWeight: FontWeight.w700)),
                  ]),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
